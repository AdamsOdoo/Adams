# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import json
import logging
import re
import threading
import time

import requests

from .rate_limiter import ShopifyRateLimiter
from .queries import shop as shop_queries

_logger = logging.getLogger(__name__)

# Retry-able HTTP status codes
RETRY_CODES = {429, 500, 502, 503}
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds

# (connect_timeout_seconds, read_timeout_seconds)
REQUEST_TIMEOUT = (10, 30)

# Allowed shop URL pattern — must be an exact .myshopify.com subdomain.
# This guards against SSRF if an attacker somehow writes a malicious
# shop_url into the DB (e.g. via a compromised admin or misconfig).
_SHOPIFY_HOST_RE = re.compile(
    r'^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$'
)

# Patterns that may contain an access token echoed back in an error body.
_TOKEN_LEAK_RE = re.compile(
    r'(shpat_[A-Za-z0-9]+|X-Shopify-Access-Token[^\s,;]*)',
    re.IGNORECASE,
)


def _sanitize_error_body(text):
    """Remove any access-token-like substrings from an error body."""
    if not text:
        return ''
    return _TOKEN_LEAK_RE.sub('[REDACTED]', text)


class ShopifyAPIError(Exception):
    """Raised when a Shopify API call fails."""

    def __init__(self, message, status_code=None, user_errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.user_errors = user_errors or []


class CircuitBreaker:
    """Thread-safe circuit breaker to prevent hammering a failing API."""

    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'closed'  # closed=normal, open=blocking, half_open=testing
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = 'closed'

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'

    def can_execute(self):
        with self._lock:
            if self.state == 'closed':
                return True
            if self.state == 'open':
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = 'half_open'
                    return True
                return False
            # half_open: allow one request to test
            return True


class ShopifyClient:
    """GraphQL Admin API client with rate limiting and retry logic."""

    def __init__(self, backend):
        # Normalise and re-validate the shop URL at call time. The model-level
        # constraint should already enforce this, but we re-check here as a
        # defence-in-depth measure: if this ever doesn't match a canonical
        # *.myshopify.com host, refuse to send the access token anywhere.
        raw = (backend.shop_url or '').strip().rstrip('/')
        if '://' in raw:
            raw = raw.split('://', 1)[1]
        host = raw.split('/')[0]
        if not _SHOPIFY_HOST_RE.match(host):
            raise ShopifyAPIError(
                "Invalid Shopify shop URL configured on backend."
            )
        self.shop_url = f"https://{host}"
        self.access_token = backend.access_token
        self.api_version = backend.api_version or '2026-01'
        self.rate_limiter = ShopifyRateLimiter()
        self.circuit_breaker = CircuitBreaker()
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token,
        })
        # Connection pooling — keep connections alive across requests
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=4,
            pool_maxsize=10,
            max_retries=0,  # We handle retries ourselves
        )
        self._session.mount('https://', adapter)

    def __repr__(self):
        return f"<ShopifyClient shop={self.shop_url}>"

    @property
    def endpoint(self):
        return f"{self.shop_url}/admin/api/{self.api_version}/graphql.json"

    def execute(self, query, variables=None, estimated_cost=10):
        """Execute a GraphQL query with rate limiting and retries.

        Returns the full parsed JSON response body.
        Raises ShopifyAPIError on failure.
        """
        if not self.circuit_breaker.can_execute():
            raise ShopifyAPIError("Circuit breaker open — API appears down. Will retry in %d seconds." % self.circuit_breaker.recovery_timeout)

        self.rate_limiter.wait_if_needed(estimated_cost)

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        last_exc = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    self.endpoint,
                    data=json.dumps(payload),
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as e:
                # Sanitise: never include the raw exception — it may embed
                # the request URL or headers (which contain the access
                # token). Log the full trace server-side and surface only a
                # generic message to the caller.
                _logger.warning(
                    "Shopify network error for %s: %s",
                    type(e).__name__, e,
                )
                last_exc = type(e).__name__
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self.circuit_breaker.record_failure()
                raise ShopifyAPIError(
                    f"Network error contacting Shopify ({last_exc})"
                )

            if resp.status_code in RETRY_CODES:
                last_exc = ShopifyAPIError(
                    f"HTTP {resp.status_code}", status_code=resp.status_code,
                )
                if attempt < MAX_RETRIES:
                    retry_after = resp.headers.get('Retry-After')
                    if retry_after:
                        try:
                            time.sleep(min(float(retry_after), 60.0))
                        except ValueError:
                            self._backoff(attempt)
                    else:
                        self._backoff(attempt)
                    continue
                self.circuit_breaker.record_failure()
                raise last_exc

            if resp.status_code != 200:
                # Strip any accidental header echoes from the error body.
                body_snippet = _sanitize_error_body(resp.text)[:500]
                raise ShopifyAPIError(
                    f"HTTP {resp.status_code}: {body_snippet}",
                    status_code=resp.status_code,
                )

            body = resp.json()

            # Update rate limiter from response
            extensions = body.get('extensions', {})
            self.rate_limiter.update_from_response(extensions)

            # Check for GraphQL-level errors
            if body.get('errors'):
                error_messages = '; '.join(
                    e.get('message', '') for e in body['errors']
                )
                raise ShopifyAPIError(f"GraphQL errors: {error_messages}")

            self.circuit_breaker.record_success()
            return body

        self.circuit_breaker.record_failure()
        raise ShopifyAPIError(f"Max retries exceeded: {last_exc}")

    def execute_mutation(self, query, variables=None, result_key=None, estimated_cost=10):
        """Execute a mutation and check userErrors.

        Returns the mutation result dict.
        Raises ShopifyAPIError if userErrors are present.
        """
        body = self.execute(query, variables, estimated_cost)
        data = body.get('data', {})

        if result_key:
            if result_key not in data:
                raise ShopifyAPIError(
                    f"Missing expected key '{result_key}' in mutation response"
                )
            result = data[result_key]
            user_errors = result.get('userErrors', [])
            if user_errors:
                messages = '; '.join(
                    f"{e.get('field', '?')}: {e.get('message', '')}"
                    for e in user_errors
                )
                raise ShopifyAPIError(
                    f"Shopify validation error: {messages}",
                    user_errors=user_errors,
                )
            return result

        return data

    def fetch_shop_info(self):
        """Fetch basic shop information for connection testing."""
        body = self.execute(shop_queries.SHOP_QUERY, estimated_cost=2)
        return body.get('data', {}).get('shop', {})

    def register_webhook(self, topic, callback_url):
        """Register a webhook subscription."""
        from .queries.webhook import WEBHOOK_CREATE_MUTATION
        return self.execute_mutation(
            WEBHOOK_CREATE_MUTATION,
            variables={'topic': topic, 'url': callback_url},
            result_key='webhookSubscriptionCreate',
            estimated_cost=10,
        )

    def fetch_paginated(self, query, connection_key, variables=None,
                        page_size=50, estimated_cost_per_page=12):
        """Generator that yields nodes from a paginated connection.

        Args:
            query: GraphQL query with $first and $after variables.
            connection_key: Dot-separated path to the connection in response,
                e.g. 'products' or 'orders'.
            variables: Additional variables besides first/after.
            page_size: Number of items per page.
            estimated_cost_per_page: Estimated cost per page request.

        Yields:
            Individual node dicts from edges.
        """
        cursor = None
        base_vars = dict(variables or {})

        while True:
            page_vars = {**base_vars, 'first': page_size}
            if cursor:
                page_vars['after'] = cursor

            body = self.execute(query, page_vars, estimated_cost_per_page)
            data = body.get('data', {})

            # Navigate to the connection
            connection = data
            for key in connection_key.split('.'):
                connection = connection.get(key, {})

            edges = connection.get('edges', [])
            for edge in edges:
                yield edge.get('node', {})

            page_info = connection.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
            if not cursor:
                _logger.warning("Missing endCursor despite hasNextPage=true, stopping pagination")
                break

    @staticmethod
    def _backoff(attempt):
        time.sleep(BACKOFF_BASE ** attempt)
