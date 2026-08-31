"""Offline P05 characterization and typed Shopify boundary tests."""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = REPO_ROOT / "addons" / "shopify_connector_core"


def _import_core_without_odoo() -> None:
    package = sys.modules.get("shopify_connector_core")
    if package is None:
        package = types.ModuleType("shopify_connector_core")
        package.__path__ = [str(CORE_ROOT)]
        package.__package__ = "shopify_connector_core"
        sys.modules["shopify_connector_core"] = package


_import_core_without_odoo()

from shopify_connector_core.integration.shopify.gateway_facade import (  # noqa: E402
    ShopifyFacadeMode,
    ShopifyGatewayFacade,
)
from shopify_connector_core.integration.shopify.graphql_executor import (  # noqa: E402
    CostMetadata,
    ERROR_API_VERSION,
    ERROR_AUTH,
    ERROR_COST_EXCEEDED,
    ERROR_DATA_SHAPE,
    GraphQLExecutor,
    MAX_COST_EXCEEDED,
    RESPONSE_TOO_LARGE,
    ShopifyGraphQLExecutionError,
    ThrottleStatus,
)
from shopify_connector_core.integration.shopify.operation_registry import (  # noqa: E402
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
    SideEffectMetadata,
)
from shopify_connector_core.integration.shopify.transport import (  # noqa: E402
    ACCESS_TOKEN_HEADER,
    CONNECT_TIMEOUT_SECONDS,
    DEFAULT_MAX_RESPONSE_BODY_BYTES,
    READ_TIMEOUT_SECONDS,
    ShopifyTransport,
    _REQUEST_EXCEPTION,
)
from shopify_connector_core.tools.api_version import (  # noqa: E402
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)


TOKEN = "shpat_P05_SYNTHETIC_TOKEN"


class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None, text=None):
        self.status_code = status_code
        self.headers = (
            {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
            if headers is None
            else headers
        )
        self._body = body
        self.text = json.dumps(body) if text is None and body is not None else (text or "")
        self.closed = False
        self.close_calls = 0

    @property
    def content(self):
        return self.text.encode("utf-8")

    def json(self):
        return self._body

    def close(self):
        self.close_calls += 1
        self.closed = True


class StreamingResponse(FakeResponse):
    def __init__(self, chunks, **kwargs):
        super().__init__(**kwargs)
        self._chunks = tuple(chunks)
        self._content_consumed = False

    def iter_content(self, chunk_size):
        del chunk_size
        yield from self._chunks


class TestShopifyTransport(unittest.TestCase):
    def test_transport_preserves_endpoint_timeout_and_allowlisted_headers(self):
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse(body={"data": {"shop": {"id": "gid"}}})

        transport = ShopifyTransport(post=post)
        response = transport.send(
            "example.myshopify.com",
            "query Shop { shop { id } }",
            {"unused": False},
            TOKEN,
            correlation_id="corr-1",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 1)
        url, kwargs = calls[0]
        self.assertEqual(
            url,
            "https://example.myshopify.com/admin/api/2026-07/graphql.json",
        )
        self.assertEqual(
            kwargs["timeout"], (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        )
        self.assertTrue(kwargs["stream"])
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["headers"][ACCESS_TOKEN_HEADER], TOKEN)
        self.assertEqual(set(kwargs["headers"]), {
            "Content-Type",
            ACCESS_TOKEN_HEADER,
            "X-Correlation-ID",
        })
        self.assertEqual(ShopifyTransport().max_response_bytes, DEFAULT_MAX_RESPONSE_BODY_BYTES)

    def test_oversized_body_is_rejected_before_json_normalization(self):
        executor = GraphQLExecutor(max_response_bytes=8)
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            executor.normalize_response(FakeResponse(body={"data": {"x": "long"}}))
        self.assertEqual(caught.exception.error_code, RESPONSE_TOO_LARGE)
        self.assertEqual(caught.exception.error_class, "unknown_system_error")

    def test_declared_response_size_fails_before_streaming(self):
        calls = []
        response = FakeResponse(
            body={"data": {}},
            headers={
                API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
                "Content-Length": "1024",
            },
        )

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return response

        transport = ShopifyTransport(post=post, max_response_bytes=64)
        with self.assertRaises(Exception) as caught:
            transport.send(
                "example.myshopify.com",
                "query Shop { shop { id } }",
                {},
                TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "response_too_large")
        self.assertEqual(len(calls), 1)
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_oversized_stream_closes_response_before_rejection(self):
        response = StreamingResponse(
            (b"12345", b"67890"),
            body={"data": {}},
        )
        transport = ShopifyTransport(
            post=lambda *args, **kwargs: response,
            max_response_bytes=8,
        )
        with self.assertRaises(Exception) as caught:
            transport.send(
                "example.myshopify.com",
                "query Shop { shop { id } }",
                {},
                TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "response_too_large")
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_stream_connection_close_is_sanitized_and_releases_response(self):
        class FailingResponse(StreamingResponse):
            def iter_content(self, chunk_size):
                del chunk_size
                yield b"partial"
                raise _REQUEST_EXCEPTION(
                    "customer@example.invalid order=1001"
                )

        response = FailingResponse((b"ignored",), body={"data": {}})
        transport = ShopifyTransport(
            post=lambda *args, **kwargs: response,
            max_response_bytes=64,
        )
        with self.assertRaises(Exception) as caught:
            transport.send(
                "example.myshopify.com",
                "query Shop { shop { id } }",
                {},
                TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "transport_error")
        self.assertEqual(caught.exception.technical_detail, "response_stream_error")
        self.assertNotIn("customer@example.invalid", caught.exception.technical_detail)
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_generic_stream_failure_is_sanitized_and_releases_response(self):
        class FailingResponse(StreamingResponse):
            def iter_content(self, chunk_size):
                del chunk_size
                yield b"partial"
                raise ValueError("customer@example.invalid order=1001")

        response = FailingResponse((b"ignored",), body={"data": {}})
        transport = ShopifyTransport(
            post=lambda *args, **kwargs: response,
            max_response_bytes=64,
        )
        with self.assertRaises(Exception) as caught:
            transport.send(
                "example.myshopify.com",
                "query Shop { shop { id } }",
                {},
                TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "transport_error")
        self.assertEqual(caught.exception.technical_detail, "response_stream_error")
        self.assertNotIn("customer@example.invalid", caught.exception.technical_detail)
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_uncacheable_stream_response_fails_closed(self):
        class UncacheableResponse(StreamingResponse):
            def __init__(self):
                super().__init__((b"bounded",), body={"data": {}})
                self._block_cache = True

            def __setattr__(self, name, value):
                if name == "_content" and getattr(self, "_block_cache", False):
                    raise RuntimeError("customer@example.invalid")
                super().__setattr__(name, value)

        response = UncacheableResponse()
        transport = ShopifyTransport(
            post=lambda *args, **kwargs: response,
            max_response_bytes=64,
        )
        with self.assertRaises(Exception) as caught:
            transport.send(
                "example.myshopify.com",
                "query Shop { shop { id } }",
                {},
                TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "transport_error")
        self.assertEqual(caught.exception.technical_detail, "response_stream_error")
        self.assertTrue(response.closed)
        self.assertEqual(response.close_calls, 1)

    def test_nonfinite_timeouts_are_rejected(self):
        for name in ("connect_timeout", "read_timeout"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(name=name, value=value):
                    kwargs = {name: value}
                    with self.assertRaises(ValueError):
                        ShopifyTransport(**kwargs)

    def test_invalid_declared_response_size_fails_closed(self):
        for declared in ("not-an-integer", "-1"):
            with self.subTest(declared=declared):
                transport = ShopifyTransport(
                    post=lambda *args, **kwargs: FakeResponse(
                        body={"data": {}},
                        headers={
                            API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
                            "Content-Length": declared,
                        },
                    ),
                )
                with self.assertRaises(Exception) as caught:
                    transport.send(
                        "example.myshopify.com",
                        "query Shop { shop { id } }",
                        {},
                        TOKEN,
                    )
                self.assertEqual(
                    caught.exception.error_code,
                    "invalid_content_length",
                )

    def test_transport_rejects_noncanonical_hosts_and_separates_request_limit(self):
        transport = ShopifyTransport(post=lambda *args, **kwargs: FakeResponse(body={}))
        for domain in (
            "example.evil.myshopify.com",
            "example.myshopify.com:443",
            "https://example.myshopify.com",
            "127.0.0.1",
            "[::1]",
            "Example.myshopify.com",
            " example.myshopify.com",
            "example.myshopify.com ",
        ):
            with self.subTest(domain=domain):
                with self.assertRaises(Exception) as caught:
                    transport.send(domain, "query Shop { shop { id } }", {}, TOKEN)
                self.assertEqual(caught.exception.error_code, "invalid_request")

        tiny = ShopifyTransport(
            post=lambda *args, **kwargs: FakeResponse(body={}),
            max_request_bytes=8,
        )
        with self.assertRaises(Exception) as caught:
            tiny.send("example.myshopify.com", "query Shop { shop { id } }", {}, TOKEN)
        self.assertEqual(caught.exception.error_code, "request_too_large")


class TestGraphQLExecutor(unittest.TestCase):
    @staticmethod
    def _registered_query_spec():
        return ShopifyOperationSpec(
            "shop.identity",
            "ShopIdentity",
            "query",
            SHOPIFY_API_VERSION,
            "query ShopIdentity { shop { id } }",
            {},
            "Result",
            "Error",
            SideEffectMetadata("observe", "Reads store identity.", False),
        )

    def test_executor_response_limit_rejects_bool_or_nonpositive_values(self):
        for value in (True, False, 0, -1, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    GraphQLExecutor(max_response_bytes=value)

    def test_cost_and_throttle_metadata_are_typed(self):
        body = {
            "data": {"shop": {"id": "gid"}},
            "extensions": {
                "cost": {
                    "requestedQueryCost": 9,
                    "actualQueryCost": 6,
                    "throttleStatus": {
                        "maximumAvailable": 1000,
                        "currentlyAvailable": 994,
                        "restoreRate": 50,
                    },
                }
            },
        }
        result = GraphQLExecutor().normalize_response(FakeResponse(body=body))
        self.assertEqual(result.requested_query_cost, 9)
        self.assertEqual(result.actual_query_cost, 6)
        self.assertEqual(result.throttle_status.currently_available, 994)
        self.assertEqual(result.cost.as_dict()["requestedQueryCost"], 9)

    def test_direct_cost_values_reject_nonfinite_numbers(self):
        with self.assertRaises(ValueError):
            CostMetadata(actual_query_cost=float("nan"))
        with self.assertRaises(ValueError):
            CostMetadata(requested_query_cost=float("inf"))
        with self.assertRaises(ValueError):
            ThrottleStatus(currently_available=float("-inf"))
        for value in (float("nan"), float("inf"), float("-inf"), "NaN"):
            with self.subTest(value=value):
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    GraphQLExecutor().normalize_response(
                        FakeResponse(body={
                            "data": {},
                            "extensions": {
                                "cost": {"actualQueryCost": value},
                            },
                        })
                    )
                self.assertEqual(
                    caught.exception.error_code,
                    "INVALID_COST_METADATA",
                )

    def test_success_requires_object_data(self):
        for body in ({}, {"data": None}, {"data": []}, {"data": "not-an-object"}):
            with self.subTest(body=body):
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    GraphQLExecutor().normalize_response(FakeResponse(body=body))
                self.assertEqual(caught.exception.error_code, "INVALID_JSON_DATA")

    def test_top_level_errors_must_be_a_list_of_objects(self):
        for errors in ("not-a-list", {"message": "wrong shape"}, None, ["wrong item"]):
            with self.subTest(errors=errors):
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    GraphQLExecutor().normalize_response(
                        FakeResponse(body={"data": {}, "errors": errors})
                    )
                self.assertEqual(
                    caught.exception.error_code,
                    "MALFORMED_GRAPHQL_ERRORS",
                )

    def test_http_200_errors_keep_legacy_classes_and_expose_shopify_code(self):
        denied = FakeResponse(body={
            "errors": [{
                "message": "Access denied",
                "extensions": {"code": "ACCESS_DENIED"},
            }]
        })
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor().normalize_response(denied)
        self.assertEqual(caught.exception.error_class, ERROR_AUTH)
        self.assertTrue(caught.exception.credential_invalid)
        self.assertEqual(caught.exception.error_code, "ACCESS_DENIED")

        exceeded = FakeResponse(body={
            "errors": [{
                "message": "Query cost exceeded",
                "extensions": {"code": MAX_COST_EXCEEDED},
            }]
        })
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor().normalize_response(exceeded)
        self.assertEqual(caught.exception.error_class, ERROR_COST_EXCEEDED)
        self.assertEqual(caught.exception.error_code, MAX_COST_EXCEEDED)
        self.assertTrue(caught.exception.is_cost_exceeded)

    def test_served_version_is_exact_and_missing_header_fails_closed(self):
        for headers in (
            {API_VERSION_RESPONSE_HEADER: "2026-10"},
            {},
        ):
            with self.subTest(headers=headers):
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    GraphQLExecutor().normalize_response(
                        FakeResponse(body={"data": {}}, headers=headers)
                    )
                self.assertEqual(caught.exception.error_class, ERROR_API_VERSION)

    def test_mutation_user_errors_are_normalized_without_raising(self):
        result = GraphQLExecutor().normalize_response(FakeResponse(body={
            "data": {
                "productUpdate": {
                    "userErrors": [{"field": ["title"], "message": "No title"}]
                }
            }
        }))
        self.assertEqual(len(result.user_errors), 1)
        self.assertEqual(result.user_errors[0].field, ("title",))

    def test_result_data_and_error_paths_are_immutable_json_values(self):
        body = {
            "data": {"items": [{"id": "gid"}]},
        }
        result = GraphQLExecutor().normalize_response(FakeResponse(body=body))
        body["data"]["items"][0]["id"] = "changed"
        self.assertEqual(result.data["items"][0]["id"], "gid")
        with self.assertRaises(TypeError):
            result.data["items"][0]["id"] = "changed"
        with self.assertRaises(TypeError):
            # GraphQL paths are immutable scalar tuples, not arbitrary JSON.
            from shopify_connector_core.integration.shopify.graphql_executor import GraphQLError
            GraphQLError("bad", path=({"secret": "x"},))

    def test_executor_copies_json_variables_and_never_repeats_transport(self):
        sent = []

        def sender(domain, document, variables, token):
            sent.append((domain, document, variables, token))
            return FakeResponse(body={"data": {"ok": True}})

        variables = {"nested": {"id": "gid"}}
        result = GraphQLExecutor(sender).execute(
            "query Check { shop { id } }",
            shop_domain="example.myshopify.com",
            access_token=TOKEN,
            variables=variables,
        )
        variables["nested"]["id"] = "changed"
        self.assertEqual(sent[0][2]["nested"]["id"], "gid")
        self.assertEqual(result.data["ok"], True)
        self.assertEqual(len(sent), 1)

    def test_invalid_variable_details_do_not_echo_request_data(self):
        pii_key = "customer@example.invalid"
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor().execute(
                "query Check { shop { id } }",
                shop_domain="example.myshopify.com",
                access_token=TOKEN,
                variables={pii_key: float("nan")},
            )
        self.assertEqual(caught.exception.error_code, "INVALID_VARIABLES")
        self.assertEqual(
            caught.exception.technical_detail,
            "variables failed JSON validation",
        )
        self.assertNotIn(pii_key, caught.exception.technical_detail)

    def test_secret_is_redacted_from_typed_error_details_and_request_repr(self):
        response = FakeResponse(
            body={"errors": [{"message": "secret %s" % TOKEN}]},
        )
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor().normalize_response(response, extra_secrets=(TOKEN,))
        self.assertNotIn(TOKEN, repr(caught.exception))
        result = GraphQLExecutor().normalize_response(FakeResponse(
            body={"data": {"echo": TOKEN}},
        ))
        self.assertNotIn(TOKEN, repr(result))
        request = ShopifyTransport(
            post=lambda *args, **kwargs: FakeResponse(body={})
        ).prepare_request(
            "example.myshopify.com",
            "query Check { shop { id } }",
            {"secret": TOKEN},
            TOKEN,
        )
        self.assertNotIn(TOKEN, repr(request))

    def test_typed_error_detail_keeps_status_and_context_but_not_raw_body(self):
        pii = "customer@example.invalid"
        response = FakeResponse(body={
            "errors": [{
                "message": "customer email %s" % pii,
                "extensions": {"code": "INTERNAL_SERVER_ERROR"},
            }],
        })
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor().normalize_response(response)
        self.assertEqual(
            caught.exception.technical_detail,
            "HTTP 200 graphql_code=INTERNAL_SERVER_ERROR",
        )
        self.assertNotIn(pii, caught.exception.technical_detail)

    def test_registered_operation_version_is_checked_before_transport(self):
        spec = ShopifyOperationSpec(
            "store.identity",
            "StoreIdentity",
            "query",
            "2025-01",
            "query StoreIdentity { shop { id } }",
            {},
            "Result",
            "Error",
            SideEffectMetadata("observe", "Reads identity.", False),
        )
        registry = ShopifyOperationRegistry((spec,))
        calls = []

        def sender(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeResponse(body={"data": {}})

        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            GraphQLExecutor(sender, operation_registry=registry).execute(
                "store.identity",
                shop_domain="example.myshopify.com",
                access_token=TOKEN,
            )
        self.assertEqual(caught.exception.error_class, ERROR_API_VERSION)
        self.assertEqual(calls, [])

    def test_configured_registry_rejects_raw_unknown_and_anonymous_operations(self):
        spec = self._registered_query_spec()
        registry = ShopifyOperationRegistry((spec,))
        sent = []

        def sender(*args, **kwargs):
            sent.append((args, kwargs))
            return FakeResponse(body={"data": {"shop": {"id": "gid"}}})

        executor = GraphQLExecutor(sender, operation_registry=registry)
        executor.execute(
            "shop.identity",
            shop_domain="example.myshopify.com",
            access_token=TOKEN,
        )
        executor.execute(
            spec,
            shop_domain="example.myshopify.com",
            access_token=TOKEN,
        )
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0][0][1], spec.document)
        self.assertEqual(sent[1][0][1], spec.document)
        unregistered_spec = ShopifyOperationSpec(
            "shop.other",
            "ShopOther",
            "query",
            SHOPIFY_API_VERSION,
            "query ShopOther { shop { name } }",
            {},
            "Result",
            "Error",
            SideEffectMetadata("observe", "Reads store name.", False),
        )

        for operation in (
            "missing.operation",
            "query RawOperation { shop { id } }",
            "mutation RawOperation { shop { id } }",
            "{ shop { id } }",
            unregistered_spec,
            object(),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    executor.execute(
                        operation,
                        shop_domain="example.myshopify.com",
                        access_token=TOKEN,
                    )
                self.assertEqual(
                    caught.exception.error_code,
                    "OPERATION_NOT_REGISTERED",
                )
        self.assertEqual(len(sent), 2)

    def test_empty_configured_registry_does_not_fall_back_to_raw_documents(self):
        sent = []

        def sender(*args, **kwargs):
            sent.append((args, kwargs))
            return FakeResponse(body={"data": {}})

        executor = GraphQLExecutor(
            sender,
            operation_registry=ShopifyOperationRegistry(),
        )
        with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
            executor.execute(
                "query RawOperation { shop { id } }",
                shop_domain="example.myshopify.com",
                access_token=TOKEN,
            )
        self.assertEqual(caught.exception.error_code, "OPERATION_NOT_REGISTERED")
        self.assertEqual(sent, [])


class TestShopifyGatewayFacade(unittest.TestCase):
    def test_legacy_and_typed_modes_delegate_once_without_credential_access(self):
        class Delegate:
            def __init__(self):
                self.calls = 0
                self.result = {
                    "data": {"shop": {"id": "gid"}},
                    "throttle_status": {
                        "maximumAvailable": 100,
                        "currentlyAvailable": 90,
                        "restoreRate": 10,
                    },
                    "cost": {
                        "requestedQueryCost": 12,
                        "actualQueryCost": 8,
                        "throttleStatus": {
                            "maximumAvailable": 100,
                            "currentlyAvailable": 90,
                            "restoreRate": 10,
                        },
                    },
                    "served_version": SHOPIFY_API_VERSION,
                }

            def execute(self, store, query, variables=None):
                self.calls += 1
                return self.result

        delegate = Delegate()
        facade = ShopifyGatewayFacade(delegate, mode=ShopifyFacadeMode.LEGACY)
        legacy_result = facade.execute(object(), "query { shop { id } }")
        self.assertIs(legacy_result, delegate.result)
        self.assertEqual(delegate.calls, 1)

        typed = facade.for_mode("typed")
        typed_result = typed.execute(object(), "query { shop { id } }")
        self.assertEqual(delegate.calls, 2)
        self.assertEqual(typed_result.requested_query_cost, 12)
        self.assertEqual(typed_result.actual_query_cost, 8)

        rollback = typed.rollback()
        self.assertEqual(rollback.mode, ShopifyFacadeMode.LEGACY)
        self.assertIs(rollback.execute(object(), "query { shop { id } }"), delegate.result)
        self.assertEqual(delegate.calls, 3)

    def test_typed_adapter_rejects_malformed_errors_and_data(self):
        for result in (
            {
                "served_version": SHOPIFY_API_VERSION,
                "data": None,
            },
            {
                "served_version": SHOPIFY_API_VERSION,
                "data": {},
                "errors": "not-a-list",
            },
            {
                "served_version": SHOPIFY_API_VERSION,
                "data": {},
                "errors": ["not-an-object"],
            },
            {
                "served_version": SHOPIFY_API_VERSION,
                "data": {"shop": {}},
                "cost": {"actualQueryCost": float("nan")},
            },
        ):
            with self.subTest(result=result):
                facade = ShopifyGatewayFacade(
                    type("Delegate", (), {
                        "execute": lambda self, *args: result,
                    })(),
                    mode=ShopifyFacadeMode.TYPED,
                )
                with self.assertRaises(ShopifyGraphQLExecutionError) as caught:
                    facade.execute(object(), "query { shop { id } }")
                self.assertIn(
                    caught.exception.error_code,
                    {
                        "INVALID_JSON_DATA",
                        "MALFORMED_GRAPHQL_ERRORS",
                        "INVALID_COST_METADATA",
                    },
                )


if __name__ == "__main__":
    unittest.main()
