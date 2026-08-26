"""Public Shopify webhook ingress: verify, persist an envelope, enqueue."""

import base64
import hashlib
import hmac
import json
import logging

from odoo import http

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from ..models.shopify_connector_webhook_secret import callback_token_digest


_logger = logging.getLogger(__name__)
MAX_WEBHOOK_BODY_BYTES = 10 * 1024 * 1024


class ShopifyConnectorWebhookController(http.Controller):
    """The only public webhook route owned by the addon."""

    @staticmethod
    def verify_hmac(raw_body, client_secret, supplied_signature):
        """Verify the exact raw bytes using constant-time comparison."""
        if not isinstance(raw_body, bytes) or not isinstance(client_secret, str):
            return False
        if not isinstance(supplied_signature, str) or not supplied_signature:
            return False
        expected = base64.b64encode(
            hmac.new(
                client_secret.encode('utf-8'), raw_body, hashlib.sha256,
            ).digest()
        ).decode('ascii')
        return hmac.compare_digest(expected, supplied_signature.strip())

    @staticmethod
    def _header(headers, name):
        value = headers.get(name)
        return value.strip() if isinstance(value, str) else False

    @staticmethod
    def read_bounded_body(http_request):
        """Read at most ``MAX_WEBHOOK_BODY_BYTES + 1`` raw bytes.

        A declared oversized body is rejected before reading.  For a bounded
        declared body, use Werkzeug's cached raw bytes: Odoo routing may have
        consumed the underlying stream before this controller runs.  An
        unknown/chunked body is still consumed in fixed chunks and rejected
        as soon as the bounded ceiling is crossed.
        """
        headers = http_request.headers
        declared = headers.get('Content-Length')
        if declared is not None:
            try:
                declared = int(declared)
            except (TypeError, ValueError):
                return False, 400
            if declared < 0:
                return False, 400
            if declared > MAX_WEBHOOK_BODY_BYTES:
                return False, 413
            # ``type='http'`` leaves an application/json payload untouched by
            # form parsing.  Read it through Werkzeug's public cache-aware API
            # rather than depending on its private ``_cached_data`` layout.
            # The declared-size ceiling above makes this read bounded.
            get_data = getattr(http_request, 'get_data', None)
            if not callable(get_data):
                return False, 400
            cached_body = get_data(cache=True, as_text=False)
            if not isinstance(cached_body, (bytes, bytearray)):
                return False, 400
            cached_body = bytes(cached_body)
            if len(cached_body) != declared:
                return False, 400
            return cached_body, 0
        stream = getattr(http_request, 'stream', None)
        if stream is None or not hasattr(stream, 'read'):
            return False, 400
        chunks = []
        total = 0
        while total <= MAX_WEBHOOK_BODY_BYTES:
            chunk = stream.read(
                min(64 * 1024, MAX_WEBHOOK_BODY_BYTES - total + 1)
            )
            if not chunk:
                break
            if not isinstance(chunk, (bytes, bytearray)):
                return False, 400
            chunk = bytes(chunk)
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_WEBHOOK_BODY_BYTES:
                return False, 413
        if declared is not None and total != declared:
            return False, 400
        return b''.join(chunks), 0

    @staticmethod
    def _response(status):
        # No diagnostic body is returned: Shopify only needs the status and
        # operators use the durable delivery/job evidence after verification.
        # Return Odoo's Response subclass.  The dispatcher recognises this
        # exact class and preserves its status; a bare Werkzeug Response is
        # coerced to a string by the route wrapper and falsely returned as 200.
        return http.Response(
            '', status=status, headers={'Content-Type': 'text/plain'},
        )

    @http.route(
        '/shopify/webhook/<string:callback_token>/<string:api_version>',
        # This is an ordinary external HTTP callback, not an Odoo JSON API.
        # With application/json, the HTTP dispatcher's form lookup does not
        # consume the body; ``read_bounded_body`` obtains the exact bytes from
        # Werkzeug's public cache-aware API before HMAC verification.
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def receive(self, callback_token, api_version, **_kwargs):
        """Verify the envelope before JSON parsing and return a fast ACK."""
        request = http.request
        http_request = request.httprequest
        # TLS is terminated before Odoo on managed Odoo.sh builds.  The WSGI
        # request therefore legitimately arrives with an internal HTTP scheme,
        # and proxy metadata is not a trustworthy application-layer security
        # boundary.  Enforcing either value here rejects genuine Shopify HTTPS
        # deliveries before callback-token lookup and HMAC verification.
        #
        # Transport confidentiality is enforced when the connector constructs
        # and registers the HTTPS-only callback URL.  Ingress authenticity is
        # then enforced below over the exact raw body by the opaque callback
        # token, API-version/store-identity gates and constant-time HMAC check.
        if api_version != SHOPIFY_API_VERSION:
            return self._response(404)

        raw_body, body_status = self.read_bounded_body(http_request)
        if body_status:
            return self._response(body_status)

        Secret = request.env['shopify.connector.webhook.secret']
        secret = Secret._find_by_token_digest(
            callback_token_digest(callback_token),
        )
        if not secret:
            return self._response(404)
        store = secret.store_id
        if not store or store.api_version != SHOPIFY_API_VERSION:
            return self._response(404)
        client_secrets = Secret._client_secrets_for_store(store)
        signature = self._header(
            http_request.headers, 'X-Shopify-Hmac-SHA256',
        )
        # This is deliberately before JSON parsing and before any metadata is
        # trusted. The current secret is tried first, then the durable previous
        # secret only while its exact grace expiry remains live.
        if not any(
            self.verify_hmac(raw_body, secret, signature)
            for secret in client_secrets
        ):
            return self._response(401)

        headers = http_request.headers
        shop_domain = self._header(headers, 'X-Shopify-Shop-Domain')
        if not shop_domain or shop_domain.lower() != store.shop_domain.lower():
            return self._response(400)
        delivered_api_version = self._header(headers, 'X-Shopify-API-Version')
        if delivered_api_version != SHOPIFY_API_VERSION:
            return self._response(400)
        delivery_id = self._header(headers, 'X-Shopify-Webhook-Id')
        topic = self._header(headers, 'X-Shopify-Topic')
        event_id = self._header(headers, 'X-Shopify-Event-Id')
        if not delivery_id or not topic:
            return self._response(400)
        registry = request.env['shopify.connector.webhook.registry']
        if not registry.topic_spec(topic):
            # Known-but-not-active topics are intentionally rejected until a
            # domain addon installs its authoritative read-first handler.
            return self._response(400)

        # HMAC has passed.  Only now may the raw body be parsed, and only a
        # strict non-PII identity allowlist is retained.
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (UnicodeDecodeError, TypeError, ValueError):
            return self._response(400)
        if not isinstance(payload, dict):
            return self._response(400)

        Delivery = request.env['shopify.connector.webhook.delivery']
        triggered_at = Delivery._parse_datetime(
            self._header(headers, 'X-Shopify-Triggered-At'),
        )
        source_updated_at = Delivery._parse_datetime(
            payload.get('updated_at') or payload.get('updatedAt'),
        )
        identity = Delivery._minimal_resource_identity(payload)
        try:
            _delivery, _duplicate = Delivery._ingest(
                store,
                delivery_id=delivery_id,
                event_id=event_id,
                topic=topic,
                shop_domain=store.shop_domain,
                api_version=delivered_api_version,
                triggered_at=triggered_at,
                source_updated_at=source_updated_at,
                payload_digest=hashlib.sha256(raw_body).hexdigest(),
                payload_size=len(raw_body),
                payload_identity=identity,
            )
        except Exception as exc:  # durable evidence/queue failure -> retry
            _logger.warning(
                'Shopify webhook ingestion failed for store %s: %s',
                store.id, type(exc).__name__,
            )
            return self._response(500)
        # No business processing, domain import, or remote read runs inline.
        return self._response(200)
