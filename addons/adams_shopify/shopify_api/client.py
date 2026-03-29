import json
import logging
import time

import requests

from .rate_limiter import ShopifyRateLimiter
from .queries import shop as shop_queries

_logger = logging.getLogger(__name__)

# Retry-able HTTP status codes
RETRY_CODES = {429, 500, 502, 503}
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class ShopifyAPIError(Exception):
    """Raised when a Shopify API call fails."""

    def __init__(self, message, status_code=None, user_errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.user_errors = user_errors or []


class CircuitBreaker:
    """Simple circuit breaker to prevent hammering a failing API."""

    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'closed'  # closed=normal, open=blocking, half_open=testing

    def record_success(self):
        self.failure_count = 0
        self.state = 'closed'

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'

    def can_execute(self):
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
        self.shop_url = backend.shop_url.rstrip('/')
        if not self.shop_url.startswith('https://'):
            self.shop_url = f"https://{self.shop_url}"
        self.access_token = backend.access_token
        self.api_version = backend.api_version or '2026-01'
        self.rate_limiter = ShopifyRateLimiter()
        self.circuit_breaker = CircuitBreaker()
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token,
        })

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
                    timeout=30,
                )
            except requests.RequestException as e:
                last_exc = e
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                self.circuit_breaker.record_failure()
                raise ShopifyAPIError(f"Network error: {e}")

            if resp.status_code in RETRY_CODES:
                last_exc = ShopifyAPIError(
                    f"HTTP {resp.status_code}", status_code=resp.status_code,
                )
                if attempt < MAX_RETRIES:
                    retry_after = resp.headers.get('Retry-After')
                    if retry_after:
                        time.sleep(float(retry_after))
                    else:
                        self._backoff(attempt)
                    continue
                self.circuit_breaker.record_failure()
                raise last_exc

            if resp.status_code != 200:
                raise ShopifyAPIError(
                    f"HTTP {resp.status_code}: {resp.text[:500]}",
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

        if result_key and result_key in data:
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

    @staticmethod
    def _backoff(attempt):
        time.sleep(BACKOFF_BASE ** attempt)
