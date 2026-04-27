# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
SimulatorClient — drop-in replacement for ShopifyClient that routes
GraphQL requests to the local Shopify Simulator endpoint instead of
a real Shopify store.
"""
import json
import logging

import requests

from odoo.addons.shopify_connector_pro.shopify_api.client import (
    ShopifyAPIError,
    ShopifyClient,
)
from odoo.addons.shopify_connector_pro.shopify_api.rate_limiter import (
    ShopifyRateLimiter,
)

_logger = logging.getLogger(__name__)


class _SimCircuitBreaker:
    """No-op circuit breaker for the simulator — always allows execution."""

    state = 'closed'
    failure_count = 0

    def can_execute(self):
        return True

    def record_success(self):
        pass

    def record_failure(self):
        pass


class SimulatorClient(ShopifyClient):
    """ShopifyClient subclass that targets the local simulator endpoint.

    Overrides URL construction so that requests go to the Odoo HTTP
    controller ``/shopify-sim/<config_id>/admin/api/…/graphql.json``
    instead of ``https://<shop>.myshopify.com/…``.

    The circuit breaker is replaced with a no-op variant because a
    local endpoint should never trip a breaker.
    """

    def __init__(self, backend):
        # Bypass the parent __init__ which validates a real myshopify.com URL.
        # We set all the same attributes manually.
        self.shop_url = (backend.shop_url or '').strip().rstrip('/')
        if not self.shop_url.startswith(('http://', 'https://')):
            self.shop_url = f"http://{self.shop_url}"
        self.access_token = backend.access_token
        self.api_version = backend.api_version or '2026-01'
        self.rate_limiter = ShopifyRateLimiter()
        self.circuit_breaker = _SimCircuitBreaker()
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token,
        })

    def __repr__(self):
        return f"<SimulatorClient endpoint={self.endpoint}>"

    @property
    def endpoint(self):
        return f"{self.shop_url}/admin/api/{self.api_version}/graphql.json"
