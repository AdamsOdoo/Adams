"""Bounded legacy-response compatibility for the Shopify API client.

The existing API client remains the public Odoo seam.  This module owns the
response/body/error projection added by P05 so the legacy model does not grow
into another hotspot.  Functions accept the model recordset explicitly; no
second transport, credential path, or domain behavior is introduced.
"""

from __future__ import annotations

import math
import re

from . import shopify_connector_api_client as legacy


_PUBLIC_ERROR_CODES = frozenset({
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


def _safe_public_error_code(value):
    """Keep response-derived error codes bounded even in a test double."""

    try:
        value = legacy._safe_error_code(value)
    except Exception:  # pragma: no cover - compatibility/double guard
        value = legacy.ERROR_CODE_UNKNOWN_GRAPHQL
    if type(value) is str:
        try:
            if value in _PUBLIC_ERROR_CODES:
                return value
        except Exception:
            pass
    return legacy.ERROR_CODE_UNKNOWN_GRAPHQL


def _invalid_response_size(response):
    legacy._close_response(response)
    raise legacy.ShopifyClientError(
        legacy.ERROR_UNKNOWN,
        legacy.REASON_UNKNOWN,
        "Shopify returned an invalid response size.",
        error_code=legacy.ERROR_CODE_INVALID_CONTENT_LENGTH,
    ) from None


def _response_stream_error(response):
    legacy._close_response(response)
    raise legacy.ShopifyClientError(
        legacy.ERROR_UNKNOWN,
        legacy.REASON_UNKNOWN,
        "response_stream_error",
        error_code=legacy.ERROR_CODE_RESPONSE_STREAM_ERROR,
    ) from None


def _declared_content_length(headers):
    """Read an integer HTTP Content-Length without coercing malformed input."""

    try:
        declared = headers.get("Content-Length")
        if declared is None:
            for key, value in headers.items():
                if str(key).lower() == "content-length":
                    declared = value
                    break
    except Exception as exc:
        raise ValueError("invalid Content-Length") from exc
    if declared is None:
        return None
    if isinstance(declared, bool):
        raise ValueError("invalid Content-Length")
    if isinstance(declared, int):
        return declared
    if not isinstance(declared, str) or not declared.strip().isdigit():
        raise ValueError("invalid Content-Length")
    return int(declared.strip(), 10)


def assert_response_body_limit(client, response):
    """Consume a streamed response with the connector's fixed byte ceiling."""

    try:
        headers = getattr(response, "headers", None) or {}
        declared = _declared_content_length(headers)
    except Exception:
        _invalid_response_size(response)
    if declared is not None and declared < 0:
        _invalid_response_size(response)
    if declared is not None and declared > legacy.MAX_RESPONSE_BODY_BYTES:
        legacy._close_response(response)
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            "Shopify response body exceeded the connector limit.",
            error_code=legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
        )

    try:
        iter_content = getattr(response, "iter_content", None)
        consumed = bool(getattr(response, "_content_consumed", False))
    except Exception:
        _response_stream_error(response)
    if callable(iter_content) and not consumed:
        chunks = []
        total = 0
        try:
            for chunk in iter_content(chunk_size=legacy._RESPONSE_CHUNK_BYTES):
                if not chunk:
                    continue
                if not isinstance(chunk, (bytes, bytearray)):
                    raise legacy.ShopifyClientError(
                        legacy.ERROR_UNKNOWN,
                        legacy.REASON_UNKNOWN,
                        "Shopify returned an invalid response body.",
                        error_code=legacy.ERROR_CODE_INVALID_RESPONSE_BODY,
                    )
                total += len(chunk)
                if total > legacy.MAX_RESPONSE_BODY_BYTES:
                    raise legacy.ShopifyClientError(
                        legacy.ERROR_UNKNOWN,
                        legacy.REASON_UNKNOWN,
                        "Shopify response body exceeded the connector limit.",
                        error_code=legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
                    )
                chunks.append(bytes(chunk))
        except legacy.ShopifyClientError:
            legacy._close_response(response)
            raise
        except legacy.requests.exceptions.RequestException:
            legacy._close_response(response)
            raise legacy.ShopifyClientError(
                legacy.ERROR_TEMPORARY,
                legacy.REASON_TEMPORARY,
                "response_stream_error",
                error_code=legacy.ERROR_CODE_RESPONSE_STREAM_ERROR,
            ) from None
        except Exception:
            legacy._close_response(response)
            raise legacy.ShopifyClientError(
                legacy.ERROR_UNKNOWN,
                legacy.REASON_UNKNOWN,
                "response_stream_error",
                error_code=legacy.ERROR_CODE_RESPONSE_STREAM_ERROR,
            ) from None
        try:
            response._content = b"".join(chunks)
            response._content_consumed = True
        except Exception:
            _response_stream_error(response)
        return True

    try:
        content = getattr(response, "content", None)
        if isinstance(content, (bytes, bytearray)):
            observed = len(content)
        else:
            text = client._safe_text(response)
            if isinstance(text, (bytes, bytearray)):
                observed = len(text)
            elif isinstance(text, str):
                observed = len(text.encode("utf-8"))
            else:
                observed = 0
    except Exception:
        _response_stream_error(response)
    if observed > legacy.MAX_RESPONSE_BODY_BYTES:
        legacy._close_response(response)
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            "Shopify response body exceeded the connector limit.",
            error_code=legacy.ERROR_CODE_RESPONSE_TOO_LARGE,
        )
    return True


def technical_detail(response, extra=None):
    """Return bounded status/request evidence without response-derived PII."""

    try:
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and not isinstance(status_code, bool):
            status = str(status_code)
        elif isinstance(status_code, str) and status_code.isdigit():
            status = status_code[:3]
        else:
            status = "unknown"
    except Exception:
        status = "unknown"
    parts = ["HTTP %s" % status]
    if isinstance(extra, str) and extra.strip():
        context = extra.strip()
        if context.startswith("requestId="):
            request_id = context[len("requestId="):].strip()
            if (
                request_id
                and len(request_id) <= 256
                and re.fullmatch(r"[A-Za-z0-9_.:/-]+", request_id)
            ):
                parts.append("requestId=%s" % request_id)
            else:
                parts.append("graphql_error")
        elif context in {
            "graphql_error",
            "malformed top-level errors",
            "graphql_request_id_present",
        }:
            parts.append(context)
        elif context.startswith("graphql_code="):
            code = context[len("graphql_code="):].strip()
            if code and len(code) <= 64 and re.fullmatch(
                r"[A-Za-z0-9_.-]+", code
            ):
                parts.append("graphql_code=" + code)
            else:
                parts.append("graphql_error")
        else:
            parts.append("graphql_error")
    return legacy.redact(" ".join(parts))


def _assert_finite_cost_value(value):
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError("Shopify cost telemetry must be numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Shopify cost telemetry must be finite")
    return value


def parse_cost_metadata(body):
    """Normalize returned query cost without changing legacy success shape."""

    if not isinstance(body, dict):
        return None
    try:
        extensions = body.get("extensions")
    except Exception as exc:
        raise ValueError("invalid cost metadata") from exc
    if extensions is None:
        return None
    if not isinstance(extensions, dict):
        raise ValueError("invalid cost metadata")
    try:
        cost = extensions.get("cost")
    except Exception as exc:
        raise ValueError("invalid cost metadata") from exc
    if cost is None:
        return None
    if not isinstance(cost, dict):
        raise ValueError("invalid cost metadata")
    try:
        requested = _assert_finite_cost_value(
            cost.get("requestedQueryCost")
        )
        actual = _assert_finite_cost_value(cost.get("actualQueryCost"))
        throttle_status = cost.get("throttleStatus")
    except Exception as exc:  # pragma: no cover - hostile mapping guard
        raise ValueError("invalid cost metadata") from exc
    normalized_throttle = None
    if throttle_status is not None:
        if not isinstance(throttle_status, dict):
            raise ValueError("invalid cost metadata")
        try:
            maximum = _assert_finite_cost_value(
                throttle_status.get("maximumAvailable")
            )
            currently = _assert_finite_cost_value(
                throttle_status.get("currentlyAvailable")
            )
            restore = _assert_finite_cost_value(
                throttle_status.get("restoreRate")
            )
        except Exception as exc:  # pragma: no cover - hostile mapping guard
            raise ValueError("invalid cost metadata") from exc
        normalized_throttle = {
            "maximumAvailable": maximum,
            "currentlyAvailable": currently,
            "restoreRate": restore,
        }
    if (
        requested is None
        and actual is None
        and (
            normalized_throttle is None
            or all(value is None for value in normalized_throttle.values())
        )
    ):
        return None
    return {
        "requestedQueryCost": requested,
        "actualQueryCost": actual,
        "throttleStatus": normalized_throttle,
    }


def parse_throttle_status(body):
    cost = parse_cost_metadata(body) or {}
    return cost.get("throttleStatus")


def record_throttle_status_isolated(client, store, throttle_status):
    """Persist telemetry after the caller transaction, preserving V1 locks."""

    commit = getattr(client.env.cr, "commit", None)
    if getattr(commit, "__name__", "") == "forbidden":
        return store._record_throttle_status(throttle_status)

    registry = client.env.registry
    uid = client.env.uid
    context = dict(client.env.context)
    store_id = store.id
    payload = dict(throttle_status)

    def persist_after_transaction():
        side_cr = registry.cursor()
        try:
            side_env = legacy.api.Environment(side_cr, uid, context)
            side_store = side_env["shopify.connector.store"].browse(
                store_id
            ).try_lock_for_update()
            if not side_store:
                side_cr.rollback()
                return False
            result = side_store._record_throttle_status(payload)
            side_cr.commit()
            return result
        except Exception:  # noqa: BLE001 - telemetry is best effort
            side_cr.rollback()
            legacy._logger.exception(
                "Could not persist deferred Shopify rate head-room for "
                "store %s; the response itself is unaffected.",
                store_id,
            )
            return False
        finally:
            side_cr.close()

    client.env.cr.postcommit.add(persist_after_transaction)
    client.env.cr.postrollback.add(persist_after_transaction)
    return True


def error_from_graphql_errors(client, errors, response, cost=None):
    """Map one bounded GraphQL error list onto the accepted legacy taxonomy."""

    if (
        not isinstance(errors, (list, tuple))
        or any(not isinstance(error, dict) for error in errors)
    ):
        return legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response, extra="malformed top-level errors"),
            credential_invalid=False,
            error_code=legacy.ERROR_CODE_MALFORMED_GRAPHQL_ERRORS,
            cost=cost,
        )
    first_error = errors[0] if errors else {}
    extensions = first_error.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
    try:
        code = extensions.get("code")
        message = first_error.get("message") or ""
        request_id = extensions.get("requestId")
    except Exception:
        code = None
        message = ""
        request_id = None
    safe_code = _safe_public_error_code(code)
    detail = technical_detail(
        response,
        extra=(
            "requestId=%s" % request_id
            if isinstance(request_id, str) and request_id
            else "graphql_error"
        ),
    )
    known = {
        "ACCESS_DENIED": (
            legacy.ERROR_AUTH, legacy.REASON_TOKEN_INVALID, True,
        ),
        "SHOP_INACTIVE": (
            legacy.ERROR_AUTH, legacy.REASON_SHOP_INACTIVE, False,
        ),
        "THROTTLED": (
            legacy.ERROR_THROTTLE, legacy.REASON_THROTTLED, False,
        ),
        "INTERNAL_SERVER_ERROR": (
            legacy.ERROR_TEMPORARY, legacy.REASON_TEMPORARY, False,
        ),
    }
    if isinstance(safe_code, str) and safe_code in known:
        error_class, reason, credential_invalid = known[safe_code]
        return legacy.ShopifyClientError(
            error_class,
            reason,
            detail,
            credential_invalid=credential_invalid,
            error_code=safe_code,
            cost=cost,
        )

    try:
        normalized_code = (
            safe_code.replace("_", "").lower()
            if isinstance(safe_code, str)
            else ""
        )
        normalized_message = (
            message.lower() if isinstance(message, str) else ""
        )
    except Exception:
        normalized_code = ""
        normalized_message = ""
    if (
        normalized_code in {
            "selectionmismatch", "schemaselection", "undefinedfield",
        }
        or "must have a selection of subfields" in normalized_message
        or "selection mismatch" in normalized_message
    ):
        return legacy.ShopifyClientError(
            legacy.ERROR_DATA_SHAPE,
            legacy.REASON_DATA_SHAPE,
            detail,
            credential_invalid=False,
            error_code=safe_code,
            cost=cost,
        )
    if safe_code == legacy.ERROR_CODE_MAX_COST_EXCEEDED:
        return legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            detail,
            credential_invalid=False,
            error_code=legacy.ERROR_CODE_MAX_COST_EXCEEDED,
            cost=cost,
        )
    return legacy.ShopifyClientError(
        legacy.ERROR_UNKNOWN,
        legacy.REASON_UNKNOWN,
        detail,
        credential_invalid=False,
        error_code=safe_code,
        cost=cost,
    )


def normalize_response(client, store, response):
    """Normalize one response before any caller can act on its data."""

    assert_response_body_limit(client, response)
    try:
        status_code = getattr(response, "status_code", None)
    except Exception:
        status_code = None
    status_errors = {
        401: (legacy.ERROR_AUTH, legacy.REASON_TOKEN_INVALID, True),
        402: (legacy.ERROR_AUTH, legacy.REASON_SHOP_FROZEN, False),
        423: (legacy.ERROR_AUTH, legacy.REASON_SHOP_LOCKED, False),
        403: (legacy.ERROR_AUTH, legacy.REASON_SHOP_FRAUDULENT, False),
        429: (legacy.ERROR_THROTTLE, legacy.REASON_THROTTLED, False),
    }
    status_error = None
    server_error = False
    status_is_ok = False
    if isinstance(status_code, int) and not isinstance(status_code, bool):
        try:
            status_error = status_errors.get(status_code)
            server_error = status_code >= 500
            status_is_ok = status_code == 200
        except Exception:
            status_error = None
            server_error = False
            status_is_ok = False
    if status_error is not None:
        error_class, reason, credential_invalid = status_error
        raise legacy.ShopifyClientError(
            error_class,
            reason,
            technical_detail(response),
            credential_invalid=credential_invalid,
        )
    if server_error:
        raise legacy.ShopifyClientError(
            legacy.ERROR_TEMPORARY,
            legacy.REASON_TEMPORARY,
            technical_detail(response),
            credential_invalid=False,
        )
    if not status_is_ok:
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response),
            credential_invalid=False,
        )

    try:
        body = response.json()
    except (ValueError, TypeError, AttributeError):
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response),
            credential_invalid=False,
            error_code=legacy.ERROR_CODE_MALFORMED_JSON,
        ) from None
    if not isinstance(body, dict):
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response),
            credential_invalid=False,
        )

    try:
        cost = parse_cost_metadata(body)
    except Exception as exc:
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response, extra="invalid_cost_metadata"),
            credential_invalid=False,
            error_code=legacy.ERROR_CODE_INVALID_COST_METADATA,
        ) from None
    errors = body.get("errors")
    if "errors" in body:
        if (
            not isinstance(errors, (list, tuple))
            or any(not isinstance(error, dict) for error in errors)
        ):
            raise legacy.ShopifyClientError(
                legacy.ERROR_UNKNOWN,
                legacy.REASON_UNKNOWN,
                technical_detail(response, extra="malformed top-level errors"),
                credential_invalid=False,
                error_code=legacy.ERROR_CODE_MALFORMED_GRAPHQL_ERRORS,
                cost=cost,
            )
        if errors:
            raise error_from_graphql_errors(client, errors, response, cost=cost)

    served_version = client._assert_served_api_version(response)
    throttle_status = (cost or {}).get("throttleStatus")
    if throttle_status and store:
        try:
            record_throttle_status_isolated(client, store, throttle_status)
        except Exception:  # noqa: BLE001 - observation is best effort
            legacy._logger.exception(
                "Could not record Shopify rate head-room for store %s; "
                "the response itself is unaffected.",
                store.id,
            )
    data = body.get("data")
    if not isinstance(data, dict):
        raise legacy.ShopifyClientError(
            legacy.ERROR_UNKNOWN,
            legacy.REASON_UNKNOWN,
            technical_detail(response, extra="invalid_json_data"),
            credential_invalid=False,
            error_code=legacy.ERROR_CODE_INVALID_JSON_DATA,
            cost=cost,
        )
    result = {
        "data": data,
        "throttle_status": throttle_status,
        "served_version": served_version,
    }
    return result


__all__ = [
    "assert_response_body_limit",
    "error_from_graphql_errors",
    "normalize_response",
    "parse_cost_metadata",
    "parse_throttle_status",
    "record_throttle_status_isolated",
    "technical_detail",
]
