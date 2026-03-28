import base64
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


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
        headers = request.httprequest.headers

        hmac_header = headers.get('X-Shopify-Hmac-Sha256', '')
        topic = headers.get('X-Shopify-Topic', '')
        webhook_id = headers.get('X-Shopify-Webhook-Id', '')
        shop_domain = headers.get('X-Shopify-Shop-Domain', '')

        # Lookup backend
        backend = request.env['shopify.backend'].sudo().browse(backend_id)
        if not backend.exists() or backend.state != 'connected':
            _logger.warning(
                "Webhook received for unknown/disconnected backend %s from %s",
                backend_id, shop_domain,
            )
            return request.make_json_response(
                {'status': 'error'}, status=404,
            )

        # Verify HMAC
        if not self._verify_hmac(raw_body, hmac_header, backend.webhook_secret):
            _logger.warning(
                "HMAC verification failed for backend %s, topic %s",
                backend_id, topic,
            )
            return request.make_json_response(
                {'status': 'unauthorized'}, status=401,
            )

        # Deduplicate by webhook_id
        if webhook_id:
            existing = request.env['shopify.webhook.log'].sudo().search([
                ('webhook_id', '=', webhook_id),
            ], limit=1)
            if existing:
                _logger.debug("Duplicate webhook %s — skipping", webhook_id)
                return request.make_json_response({'status': 'ok'})

        # Parse payload
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, ValueError):
            payload = {}

        # Extract the resource Shopify ID from the payload
        shopify_resource_id = str(payload.get('id', '')) if payload else ''

        # Enqueue
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
