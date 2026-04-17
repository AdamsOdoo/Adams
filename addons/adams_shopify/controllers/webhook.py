# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import hmac
import json
import logging
import threading
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Rate limiter for webhook endpoint ──────────────────────
# Per-backend rate limiting: max requests within a time window
_webhook_rate_buckets = {}  # {backend_id: [timestamps]}
_webhook_rate_lock = threading.Lock()
WEBHOOK_RATE_LIMIT = 200  # max requests per window
WEBHOOK_RATE_WINDOW = 60  # seconds
# Maximum number of distinct backend IDs tracked, to prevent an attacker
# from OOMing the dict by spamming random IDs.
WEBHOOK_RATE_MAX_BUCKETS = 1000

# Maximum webhook payload size (10 MB)
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024


def _check_rate_limit(backend_id):
    """Return True if the request is allowed, False if rate-limited.

    Thread-safe: guarded by a module-level lock because Odoo webhook
    workers share process memory.
    """
    now = time.time()
    cutoff = now - WEBHOOK_RATE_WINDOW
    with _webhook_rate_lock:
        # Evict oldest buckets if dict has grown too large
        if len(_webhook_rate_buckets) > WEBHOOK_RATE_MAX_BUCKETS:
            # Drop any buckets whose newest entry is already expired
            stale = [
                k for k, ts in _webhook_rate_buckets.items()
                if not ts or ts[-1] < cutoff
            ]
            for k in stale:
                _webhook_rate_buckets.pop(k, None)
        bucket = _webhook_rate_buckets.get(backend_id, [])
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

        headers = request.httprequest.headers
        hmac_header = headers.get('X-Shopify-Hmac-Sha256', '')
        topic = headers.get('X-Shopify-Topic', '')
        webhook_id = headers.get('X-Shopify-Webhook-Id', '')
        shop_domain_header = headers.get('X-Shopify-Shop-Domain', '')

        # Lookup backend
        backend = request.env['shopify.backend'].sudo().browse(backend_id)
        if not backend.exists() or backend.state != 'connected':
            return request.make_json_response(
                {'status': 'error'}, status=404,
            )

        # ── Shop domain sanity check ────────────────────────
        # Reject webhooks whose shop domain header doesn't match the backend.
        # Shopify always sends this header; a mismatch indicates a misrouted
        # or forged request.
        if shop_domain_header and backend.shop_url:
            expected = (backend.shop_url or '').strip().lower()
            if '://' in expected:
                expected = expected.split('://', 1)[1]
            expected = expected.split('/')[0]
            if shop_domain_header.strip().lower() != expected:
                _logger.warning(
                    "Webhook shop domain mismatch for backend %s: got %s, expected %s",
                    backend_id, shop_domain_header, expected,
                )
                return request.make_json_response(
                    {'status': 'error'}, status=404,
                )

        # ── HMAC verification (BEFORE rate limit to avoid DoS on rate dict) ─
        if not self._verify_hmac(raw_body, hmac_header, backend.webhook_secret):
            _logger.warning(
                "HMAC verification failed for backend %s, topic %s",
                backend_id, topic,
            )
            return request.make_json_response(
                {'status': 'unauthorized'}, status=401,
            )

        # ── Rate limiting (after HMAC so unauth cannot poison the bucket) ──
        if not _check_rate_limit(backend_id):
            _logger.warning(
                "Webhook rate limit exceeded for backend %s", backend_id,
            )
            return request.make_json_response(
                {'status': 'error', 'message': 'Rate limit exceeded'}, status=429,
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


class ShopifyHealthController(http.Controller):
    """Lightweight health-check endpoint for monitoring.

    Returns connection status and summary sync stats for a backend.
    No authentication required beyond Odoo session.
    """

    @http.route(
        '/shopify/health/<int:backend_id>',
        type='http', auth='user', methods=['GET'],
    )
    def health_check(self, backend_id):
        backend = request.env['shopify.backend'].sudo().browse(backend_id)
        if not backend.exists():
            return request.make_json_response(
                {'status': 'not_found'}, status=404,
            )

        data = {
            'status': 'ok' if backend.state == 'connected' else backend.state,
            'shop_name': backend.shop_name or '',
            'last_sync': backend.last_sync_date and str(backend.last_sync_date) or None,
            'sync_health_pct': backend.sync_health_pct,
            'counts': {
                'products': backend.product_bind_count,
                'customers': backend.customer_bind_count,
                'orders': backend.order_bind_count,
                'inventory': backend.inventory_bind_count,
                'collections': backend.collection_bind_count,
                'refunds': backend.refund_bind_count,
                'payouts': backend.payout_count,
                'errors': backend.total_error_count,
                'permanent_errors': backend.permanent_error_count,
                'pending': backend.total_pending_count,
            },
            'errors_by_entity': {
                'products': backend.product_error_count,
                'customers': backend.customer_error_count,
                'orders': backend.order_error_count,
                'inventory': backend.inventory_error_count,
            },
            'last_sync_per_entity': {
                'products': backend.last_product_sync and str(backend.last_product_sync) or None,
                'customers': backend.last_customer_sync and str(backend.last_customer_sync) or None,
                'orders': backend.last_order_sync and str(backend.last_order_sync) or None,
                'inventory': backend.last_inventory_sync and str(backend.last_inventory_sync) or None,
                'fulfillments': backend.last_fulfillment_sync and str(backend.last_fulfillment_sync) or None,
                'collections': backend.last_collection_sync and str(backend.last_collection_sync) or None,
            },
            'webhooks': {
                'pending': backend.webhook_pending_count,
                'dead_letters': backend.webhook_dead_letter_count,
            },
            'data_integrity': {
                'payment_mismatches': backend.payment_mismatch_count,
                'fulfillment_mismatches': backend.fulfillment_mismatch_count,
            },
        }

        status_code = 200 if backend.state == 'connected' else 503
        return request.make_json_response(data, status=status_code)
