import requests

from odoo import api, models
from odoo.exceptions import UserError

from ..tools.redaction import redact

# Adjustable planning defaults (not an official Shopify requirement).
_CONNECT_TIMEOUT_SECONDS = 10
_READ_TIMEOUT_SECONDS = 20

# The fixed 16-class error_class registry (DEC-009) -- only the four
# classes below are ever raised by this client; identity-mismatch
# (`odoo_validation_configuration`) is interpreted by
# `action_test_connection()` from a successful `execute()` response, not
# raised here.
ERROR_TEMPORARY = 'shopify_temporary_server_network'
ERROR_AUTH = 'shopify_permission_scope_auth'
ERROR_THROTTLE = 'shopify_throttling_rate_limit'
ERROR_UNKNOWN = 'unknown_system_error'

# The five mandatory, pairwise-distinct plain-language reasons for the
# shopify_permission_scope_auth class (AR-027, F1 revision) -- a shared/
# generic string across any two of them is a review failure.
REASON_TOKEN_INVALID = (
    'Your access token appears invalid or was revoked — replace it.'
)
REASON_SHOP_FROZEN = (
    'Shopify has frozen this store, most commonly for a billing/payment '
    'issue — resolve it in Shopify, then retry.'
)
REASON_SHOP_LOCKED = 'This store has been locked by Shopify.'
REASON_SHOP_FRAUDULENT = 'Shopify has flagged this store as fraudulent.'
REASON_SHOP_INACTIVE = 'This store is inactive.'

REASON_TEMPORARY = (
    'Shopify could not be reached right now — this is usually temporary.'
)
# THROTTLED/429 body shape is unofficial/unconfirmed -- see Open question
# #1/#3, credential-connection-api-client-planning.md.
REASON_THROTTLED = 'Shopify is asking us to slow down — try again shortly.'
REASON_UNKNOWN = (
    'Shopify returned a response we could not interpret — try again, '
    'and contact support if it persists.'
)


class ShopifyClientError(Exception):
    """Normalized error raised by `shopify.connector.api.client.execute()`.

    Attributes: `error_class` (one of the fixed 16), `reason` (the
    plain-language safe message), `technical_detail` (redacted; carries
    `extensions.requestId` when present, otherwise a redacted status/body
    excerpt), and `credential_invalid` (bool, default False -- set only
    for a genuine token-invalid signal, never for a shop-account-state
    condition). `str(exc)` returns `reason` only -- never the technical
    detail, never a header, never the token.
    """

    def __init__(
        self, error_class, reason, technical_detail=False,
        credential_invalid=False,
    ):
        reason = redact(reason)
        super().__init__(reason)
        self.error_class = error_class
        self.reason = reason
        self.technical_detail = (
            redact(technical_detail) if technical_detail else technical_detail
        )
        self.credential_invalid = credential_invalid

    def __str__(self):
        return self.reason


class ShopifyConnectorApiClient(models.AbstractModel):
    """Read-only Shopify Admin GraphQL transport boundary (Task 003).

    Stateless, no table. `execute()` is the only public entry point;
    `_send()` is the only method containing an actual HTTP call and is
    the transport-injection seam tests override. No method on this
    model can construct a request body containing the substring
    `mutation` -- there is no mutation-capable method, no retry loop
    (retry policy belongs to the job layer, DEC-009), no domain-sync
    method, and no `sudo()` (the two sanctioned sites in this task live
    elsewhere: the pre-existing Task 002 `_get_access_token`, and the
    new job-log `_system_append`).
    """

    _name = 'shopify.connector.api.client'
    _description = 'Shopify Connector API Client'

    @api.model
    def execute(self, store, query, variables=None):
        """Send one read-only GraphQL query and return its normalized data.

        Returns `{'data': <parsed data>, 'throttle_status': <dict or
        None>}`, optionally with `version_fallforward`/`served_version`
        keys on an API-version header mismatch (never raised as an
        error). Raises `ShopifyClientError` on any transport or
        GraphQL-level failure.
        """
        if not store.shop_domain or not store.api_version:
            raise UserError(
                'A shop domain and API version are required before '
                'contacting Shopify.'
            )
        token = self.env['shopify.connector.store.credential']._get_access_token(
            store
        )
        if not token:
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        body = {'query': query, 'variables': variables or {}}
        try:
            response = self._send(store, body)
        except ShopifyClientError:
            raise
        except requests.exceptions.RequestException as exc:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=redact(str(exc)),
            )
        return self._normalize_response(store, response)

    @api.model
    def _send(self, store, body):
        """The only method containing an actual HTTP call.

        Sends an HTTPS POST to the store's versioned GraphQL endpoint
        with bounded timeouts. Returns the raw HTTP response object
        (status, headers, body) or raises a transport-level error (DNS,
        TLS, connect, timeout) that `execute()` normalizes. Never logs
        the request headers or body.
        """
        token = self.env['shopify.connector.store.credential']._get_access_token(
            store
        )
        url = 'https://%s/admin/api/%s/graphql.json' % (
            store.shop_domain, store.api_version,
        )
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': token,
        }
        return requests.post(
            url,
            json=body,
            headers=headers,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )

    def _safe_text(self, response):
        try:
            return response.text or ''
        except Exception:
            return ''

    def _technical_detail(self, response, extra=None):
        parts = ['HTTP %s' % getattr(response, 'status_code', 'unknown')]
        if extra:
            parts.append(str(extra))
        body_excerpt = self._safe_text(response)
        if body_excerpt:
            parts.append(body_excerpt)
        return redact(' '.join(parts))

    def _parse_throttle_status(self, body):
        # Verbatim official field names; never hard-coded bucket sizes
        # (MBQ-51 stays untouched -- this only surfaces the signal).
        extensions = body.get('extensions') or {}
        cost = extensions.get('cost') or {}
        throttle_status = cost.get('throttleStatus')
        if not throttle_status:
            return None
        return {
            'maximumAvailable': throttle_status.get('maximumAvailable'),
            'currentlyAvailable': throttle_status.get('currentlyAvailable'),
            'restoreRate': throttle_status.get('restoreRate'),
        }

    def _error_from_graphql_errors(self, errors, response):
        first_error = errors[0] if errors else {}
        extensions = first_error.get('extensions') or {}
        code = extensions.get('code')
        request_id = extensions.get('requestId')
        extra = 'requestId=%s' % request_id if request_id else first_error.get('message')
        technical_detail = self._technical_detail(response, extra=extra)
        if code == 'ACCESS_DENIED':
            return ShopifyClientError(
                ERROR_AUTH, REASON_TOKEN_INVALID, technical_detail,
                credential_invalid=True,
            )
        if code == 'SHOP_INACTIVE':
            return ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_INACTIVE, technical_detail,
                credential_invalid=False,
            )
        if code == 'THROTTLED':
            return ShopifyClientError(
                ERROR_THROTTLE, REASON_THROTTLED, technical_detail,
                credential_invalid=False,
            )
        if code == 'INTERNAL_SERVER_ERROR':
            return ShopifyClientError(
                ERROR_TEMPORARY, REASON_TEMPORARY, technical_detail,
                credential_invalid=False,
            )
        # MAX_COST_EXCEEDED on this tiny query, and anything unclassifiable
        # (incl. an unknown extensions.code), fall to the single
        # safety-net path per DEC-009 -- no 17th class is introduced.
        return ShopifyClientError(
            ERROR_UNKNOWN, REASON_UNKNOWN, technical_detail,
            credential_invalid=False,
        )

    def _normalize_response(self, store, response):
        status_code = getattr(response, 'status_code', None)
        if status_code == 401:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_TOKEN_INVALID,
                self._technical_detail(response), credential_invalid=True,
            )
        if status_code == 402:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_FROZEN,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 423:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_LOCKED,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 403:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_FRAUDULENT,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 429:
            raise ShopifyClientError(
                ERROR_THROTTLE, REASON_THROTTLED,
                self._technical_detail(response), credential_invalid=False,
            )
        if isinstance(status_code, int) and status_code >= 500:
            raise ShopifyClientError(
                ERROR_TEMPORARY, REASON_TEMPORARY,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code != 200:
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )

        try:
            body = response.json()
        except ValueError:
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )
        if not isinstance(body, dict):
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )

        errors = body.get('errors')
        if errors:
            raise self._error_from_graphql_errors(errors, response)

        result = {
            'data': body.get('data'),
            'throttle_status': self._parse_throttle_status(body),
        }
        served_version = None
        headers = getattr(response, 'headers', None) or {}
        try:
            served_version = headers.get('X-Shopify-API-Version')
        except Exception:
            served_version = None
        if served_version and served_version != store.api_version:
            result['version_fallforward'] = True
            result['served_version'] = served_version
        return result
