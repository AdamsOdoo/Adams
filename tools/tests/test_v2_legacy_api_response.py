"""Dependency-free tests for the legacy API response compatibility seam."""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESPONSE_PATH = (
    REPO_ROOT
    / "addons"
    / "shopify_connector_core"
    / "models"
    / "shopify_connector_api_response.py"
)


def _load_response_module():
    """Load the response module with a deliberately tiny legacy stub."""

    package_name = "_legacy_api_response_test_package"
    models_name = package_name + ".models"
    legacy_name = models_name + ".shopify_connector_api_client"
    package = types.ModuleType(package_name)
    package.__path__ = [str(RESPONSE_PATH.parent)]
    models = types.ModuleType(models_name)
    models.__path__ = [str(RESPONSE_PATH.parent)]
    legacy = types.ModuleType(legacy_name)

    legacy.ERROR_TEMPORARY = "shopify_temporary_server_network"
    legacy.ERROR_AUTH = "shopify_permission_scope_auth"
    legacy.ERROR_THROTTLE = "shopify_throttling_rate_limit"
    legacy.ERROR_UNKNOWN = "unknown_system_error"
    legacy.ERROR_DATA_SHAPE = "data_shape_schema_mismatch"
    legacy.REASON_TOKEN_INVALID = "token invalid"
    legacy.REASON_SHOP_FROZEN = "shop frozen"
    legacy.REASON_SHOP_LOCKED = "shop locked"
    legacy.REASON_SHOP_FRAUDULENT = "shop fraudulent"
    legacy.REASON_SHOP_INACTIVE = "shop inactive"
    legacy.REASON_THROTTLED = "throttled"
    legacy.REASON_TEMPORARY = "temporary"
    legacy.REASON_UNKNOWN = "unknown"
    legacy.REASON_DATA_SHAPE = "data shape"
    legacy.ERROR_CODE_MAX_COST_EXCEEDED = "MAX_COST_EXCEEDED"
    legacy.ERROR_CODE_RESPONSE_TOO_LARGE = "response_too_large"
    legacy.ERROR_CODE_INVALID_CONTENT_LENGTH = "invalid_content_length"
    legacy.ERROR_CODE_UNKNOWN_GRAPHQL = "UNKNOWN_GRAPHQL_ERROR"
    legacy.ERROR_CODE_MALFORMED_JSON = "MALFORMED_JSON"
    legacy.ERROR_CODE_INVALID_RESPONSE_BODY = "INVALID_RESPONSE_BODY"
    legacy.ERROR_CODE_RESPONSE_STREAM_ERROR = "RESPONSE_STREAM_ERROR"
    legacy.ERROR_CODE_INVALID_COST_METADATA = "INVALID_COST_METADATA"
    legacy.ERROR_CODE_MALFORMED_GRAPHQL_ERRORS = "MALFORMED_GRAPHQL_ERRORS"
    legacy.ERROR_CODE_INVALID_JSON_DATA = "INVALID_JSON_DATA"
    legacy.MAX_RESPONSE_BODY_BYTES = 10 * 1024 * 1024
    legacy._RESPONSE_CHUNK_BYTES = 64 * 1024
    legacy._logger = logging.getLogger(__name__)
    legacy.redact = lambda value: value
    legacy._close_response = lambda response: response.close()
    legacy.requests = types.SimpleNamespace(
        exceptions=types.SimpleNamespace(RequestException=OSError),
    )

    safe_codes = frozenset({
        legacy.ERROR_CODE_MAX_COST_EXCEEDED,
        legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
        legacy.ERROR_CODE_INVALID_CONTENT_LENGTH,
        legacy.ERROR_CODE_UNKNOWN_GRAPHQL,
        legacy.ERROR_CODE_MALFORMED_JSON,
        legacy.ERROR_CODE_INVALID_RESPONSE_BODY,
        legacy.ERROR_CODE_RESPONSE_STREAM_ERROR,
        legacy.ERROR_CODE_INVALID_COST_METADATA,
        legacy.ERROR_CODE_MALFORMED_GRAPHQL_ERRORS,
        legacy.ERROR_CODE_INVALID_JSON_DATA,
        "ACCESS_DENIED",
        "SHOP_INACTIVE",
        "THROTTLED",
        "INTERNAL_SERVER_ERROR",
        "selectionMismatch",
        "schemaSelection",
        "undefinedField",
    })

    def safe_error_code(value):
        if isinstance(value, str):
            try:
                if value in safe_codes:
                    return value
            except TypeError:
                pass
        return legacy.ERROR_CODE_UNKNOWN_GRAPHQL

    legacy._safe_error_code = safe_error_code

    class LegacyError(Exception):
        def __init__(self, error_class, reason, detail, **kwargs):
            self.error_class = error_class
            self.reason = reason
            self.technical_detail = detail
            self.error_code = kwargs.get("error_code")
            self.code = self.error_code
            self.shopify_error_code = self.error_code
            self.classification_code = self.error_code
            self.cost = kwargs.get("cost")
            super().__init__(reason)

    legacy.ShopifyClientError = LegacyError
    legacy.api = types.SimpleNamespace(Environment=object)
    package.models = models
    models.shopify_connector_api_client = legacy
    sys.modules[package_name] = package
    sys.modules[models_name] = models
    sys.modules[legacy_name] = legacy

    module_name = models_name + ".shopify_connector_api_response"
    spec = importlib.util.spec_from_file_location(module_name, RESPONSE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return legacy, module


class FakeResponse:
    def __init__(
        self,
        body=None,
        status_code=200,
        headers=None,
        json_exception=None,
        stream_chunks=None,
        text=None,
    ):
        self.status_code = status_code
        self.headers = (
            {"X-Shopify-API-Version": "2026-07"}
            if headers is None
            else headers
        )
        self.body = body
        self.json_exception = json_exception
        self.text = text if text is not None else ""
        self.stream_chunks = stream_chunks
        self._content_consumed = stream_chunks is None
        self.closed = False
        self.close_calls = 0

    def json(self):
        if self.json_exception is not None:
            raise self.json_exception
        return self.body

    def iter_content(self, chunk_size):
        del chunk_size
        if self.stream_chunks is not None:
            yield from self.stream_chunks

    def close(self):
        self.close_calls += 1
        self.closed = True


class ClientStub:
    def _safe_text(self, response):
        return response.text or ""

    def _assert_served_api_version(self, response):
        del response
        return "2026-07"


class TestLegacyApiResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy, cls.response = _load_response_module()
        cls.client = ClientStub()

    def _error(self, response):
        with self.assertRaises(self.legacy.ShopifyClientError) as caught:
            self.response.normalize_response(self.client, None, response)
        return caught.exception

    def test_cost_does_not_change_the_legacy_success_shape(self):
        result = self.response.normalize_response(
            self.client,
            None,
            FakeResponse(body={
                "data": {"shop": {"id": "gid://shopify/Shop/1"}},
                "extensions": {"cost": {
                    "requestedQueryCost": 8,
                    "actualQueryCost": 6,
                    "throttleStatus": {
                        "maximumAvailable": 100,
                        "currentlyAvailable": 94,
                        "restoreRate": 5,
                    },
                }},
            }),
        )
        self.assertEqual(
            set(result), {"data", "throttle_status", "served_version"},
        )
        self.assertEqual(result["throttle_status"]["currentlyAvailable"], 94)

    def test_unknown_graphql_code_and_unhashable_status_are_safe(self):
        error = self._error(FakeResponse(body={
            "errors": [{"extensions": {"code": ["remote-secret"]}}],
        }))
        self.assertEqual(error.error_code, self.legacy.ERROR_CODE_UNKNOWN_GRAPHQL)
        self.assertEqual(error.code, self.legacy.ERROR_CODE_UNKNOWN_GRAPHQL)
        self.assertEqual(error.shopify_error_code, error.error_code)

        for status_code in ({"status": 401}, [401]):
            with self.subTest(status_code=status_code):
                error = self._error(FakeResponse(
                    body={"data": {}}, status_code=status_code,
                ))
                self.assertEqual(error.error_class, self.legacy.ERROR_UNKNOWN)

    def test_json_typeerror_and_attributeerror_are_normalized(self):
        for exception in (TypeError("bad json"), AttributeError("no json")):
            with self.subTest(exception=type(exception).__name__):
                error = self._error(FakeResponse(json_exception=exception))
                self.assertEqual(error.error_code, self.legacy.ERROR_CODE_MALFORMED_JSON)

    def test_cost_strings_booleans_and_nonfinite_values_fail_closed(self):
        for value in ("42", True, float("nan"), float("inf")):
            with self.subTest(value=value):
                error = self._error(FakeResponse(body={
                    "data": {},
                    "extensions": {"cost": {"actualQueryCost": value}},
                }))
                self.assertEqual(
                    error.error_code,
                    self.legacy.ERROR_CODE_INVALID_COST_METADATA,
                )
                self.assertIsNone(error.cost)

    def test_invalid_content_length_is_not_too_large(self):
        original_limit = self.legacy.MAX_RESPONSE_BODY_BYTES
        self.legacy.MAX_RESPONSE_BODY_BYTES = 8
        try:
            for value in ("not-an-integer", "-1", True, 1.5):
                with self.subTest(value=value):
                    response = FakeResponse(
                        body={"data": {}},
                        headers={"Content-Length": value},
                    )
                    error = self._error(response)
                    self.assertEqual(
                        error.error_code,
                        self.legacy.ERROR_CODE_INVALID_CONTENT_LENGTH,
                    )
                    self.assertTrue(response.closed)

            response = FakeResponse(
                body={"data": {}}, headers={"Content-Length": "9"},
            )
            error = self._error(response)
            self.assertEqual(
                error.error_code, self.legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
            )
            self.assertTrue(response.closed)

            response = FakeResponse(
                body={"data": {}}, stream_chunks=(b"12345", b"67890"),
            )
            error = self._error(response)
            self.assertEqual(
                error.error_code, self.legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
            )
            self.assertTrue(response.closed)
        finally:
            self.legacy.MAX_RESPONSE_BODY_BYTES = original_limit


if __name__ == "__main__":
    unittest.main()
