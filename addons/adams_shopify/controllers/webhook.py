import base64
import hashlib
import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Rate limiter for webhook endpoint ──────────────────────
# Per-backend rate limiting: max requests within a time window
_webhook_rate_buckets = {}  # {backend_id: [timestamps]}
WEBHOOK_RATE_LIMIT = 200  # max requests per window
WEBHOOK_RATE_WINDOW = 60  # seconds

# Maximum webhook payload size (10 MB)
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024


def _check_rate_limit(backend_id):
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    bucket = _webhook_rate_buckets.get(backend_id, [])
    # Prune old entries
    cutoff = now - WEBHOOK_RATE_WINDOW
    bucket = [t for t in bucket if t > cutoff]
    if len(bucket) >= WEBHOOK_RATE_LIMIT:
        _webhook_rate_buckets[backend_id] = bucket
        return False
    bucket.append(now)
    _webhook_rate_buckets[backend_id] = bucket
    return True


class ShopifyWebhookController(http.Controller):

    @http.route(
        '/shopify/webhook/<int:backend_id>',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def handle_webhook(self, backend_id, **kwargs):
        """Receive Shopify webhook, verify HMAC, enqueue for processing."""
        raw_body = request.httprequest.get_data()

        # ── Payload size check ──────────────────────────────
        if len(raw_body) > MAX_PAYLOAD_SIZE:
            _logger.warning(
                "Webhook payload too large (%d bytes) for backend %s",
                len(raw_body), backend_id,
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Payload too large'}, status=413,
            )

        # ── Rate limiting ───────────────────────────────────
        if not _check_rate_limit(backend_id):
            _logger.warning(
                "Webhook rate limit exceeded for backend %s", backend_id,
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Rate limit exceeded'}, status=429,
            )

        headers = request.httprequest.headers
        hmac_header = headers.get('X-Shopify-Hmac-Sha256', '')
        topic = headers.get('X-Shopify-Topic', '')
        webhook_id = headers.get('X-Shopify-Webhook-Id', '')

        # Lookup backend
        backend = request.env['shopify.backend'].sudo().browse(backend_id)
        if not backend.exists() or backend.state != 'connected':
            return request.make_json_response(
                {'status': 'error'}, status=404,
            )

        # ── HMAC verification ───────────────────────────────
        if not self._verify_hmac(raw_body, hmac_header, backend.webhook_secret):
            _logger.warning(
                "HMAC verification failed for backend %s, topic %s",
                backend_id, topic,
            )
            return request.make_json_response(
                {'status': 'unauthorized'}, status=401,
            )

        # ── Deduplicate by webhook_id ───────────────────────
        if webhook_id:
            existing = request.env['shopify.webhook.log'].sudo().search([
                ('webhook_id', '=', webhook_id),
            ], limit=1)
            if existing:
                return request.make_json_response({'status': 'ok'})

        # ── Parse payload ───────────────────────────────────
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, ValueError):
            payload = {}

        shopify_resource_id = str(payload.get('id', '')) if payload else ''

        # ── Enqueue ─────────────────────────────────────────
        try:
            request.env['shopify.webhook.log'].sudo().create({
                'backend_id': backend_id,
                'webhook_id': webhook_id,
                'topic': topic,
                'shopify_id': shopify_resource_id,
                'payload': json.dumps(payload),
                'state': 'pending',
            })
        except Exception:
            # IntegrityError from unique constraint = duplicate, which is fine
            _logger.debug("Webhook %s already exists (race condition)", webhook_id)

        # Return 200 immediately — processing happens via cron
        return request.make_json_response({'status': 'ok'})

    @staticmethod
    def _verify_hmac(raw_body, hmac_header, secret):
        """Verify Shopify webhook HMAC-SHA256 signature.

        Uses hmac.compare_digest for timing-safe comparison.
        """
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
