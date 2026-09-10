"""Pure validation and metadata contracts for V2 run evidence.

The ORM model imports these names to keep its file focused on persistence
and lifecycle transitions while preserving the original module API.
"""

import json
import math
import re

from odoo.exceptions import ValidationError

from ..tools.redaction import redact


RUN_WORKFLOW_SELECTION = [
    ('core', 'Core'),
    ('product', 'Product'),
    ('product_export', 'Product Export'),
    ('sale', 'Sales'),
    ('inventory', 'Inventory'),
    ('fulfillment', 'Fulfillment'),
    ('webhook', 'Webhook'),
]

RUN_TRIGGER_SELECTION = [
    ('user', 'User'),
    ('cron', 'Scheduled Job'),
    ('webhook', 'Webhook'),
    ('odoo_event', 'Odoo Event'),
    ('reconciliation', 'Reconciliation'),
    ('system', 'System'),
]

RUN_STATE_SELECTION = [
    ('requested', 'Requested'),
    ('admitted', 'Admitted'),
    ('running', 'Running'),
    ('waiting', 'Waiting'),
    ('succeeded', 'Succeeded'),
    ('partially_succeeded', 'Partially Succeeded'),
    ('failed_retryable', 'Failed (Retryable)'),
    ('blocked_manual_review', 'Blocked - Manual Review'),
    ('failed_terminal', 'Failed (Terminal)'),
    ('cancelled', 'Cancelled'),
]
RUN_STATE_KEYS = frozenset(item[0] for item in RUN_STATE_SELECTION)

RUN_TERMINAL_STATES = frozenset((
    'succeeded',
    'partially_succeeded',
    'failed_terminal',
    'cancelled',
))

RUN_LEGAL_TRANSITIONS = {
    'requested': frozenset(('admitted', 'cancelled')),
    'admitted': frozenset((
        'running', 'waiting', 'failed_retryable',
        'blocked_manual_review', 'partially_succeeded', 'failed_terminal',
        'cancelled',
    )),
    'running': frozenset((
        'waiting', 'succeeded', 'partially_succeeded',
        'failed_retryable', 'blocked_manual_review',
        'failed_terminal', 'cancelled',
    )),
    'waiting': frozenset((
        'admitted', 'running', 'failed_retryable',
        'blocked_manual_review', 'partially_succeeded', 'failed_terminal',
        'cancelled',
    )),
    'failed_retryable': frozenset(('admitted', 'cancelled')),
    'blocked_manual_review': frozenset(('admitted', 'cancelled')),
    'succeeded': frozenset(),
    'partially_succeeded': frozenset(),
    'failed_terminal': frozenset(),
    'cancelled': frozenset(),
}

# A context value is not an authorization mechanism by itself.  The object
# identity is what closes this ORM surface: a serialized RPC value can never
# be the same Python object.  `env.su` is intentional because the caller has
# already crossed a named internal service boundary and ACLs are added by the
# owning integration change.
RUN_WRITE_CONTEXT = 'shopify_connector_run_write_surface'
RUN_SERVICE_SENTINEL_CONTEXT = 'shopify_connector_run_service_sentinel'
RUN_SERVICE_SENTINEL = object()
RUN_CREATE_SURFACE = '_create_run'
RUN_FINALIZE_NAME_SURFACE = '_finalize_run_name'
RUN_WRITE_SURFACES = frozenset((
    RUN_CREATE_SURFACE,
    RUN_FINALIZE_NAME_SURFACE,
    '_admit_run',
    '_transition_run',
    '_finish_run',
    '_request_cancel',
))

RUN_SURFACE_FIELDS = {
    # Creation values are accepted only by `create()`.  This surface can
    # never be used to mutate an existing row.
    RUN_CREATE_SURFACE: frozenset(),
    RUN_FINALIZE_NAME_SURFACE: frozenset(('name',)),
    '_admit_run': frozenset(('state', 'admitted_at')),
    '_transition_run': frozenset((
        'state', 'admitted_at', 'finished_at', 'result_summary',
    )),
    '_finish_run': frozenset(('state', 'finished_at', 'result_summary')),
    '_request_cancel': frozenset((
        'cancel_requested_at', 'cancel_requested_by', 'cancel_reason',
    )),
}

RUN_CREATE_LIFECYCLE_FIELDS = frozenset((
    'admitted_at', 'finished_at', 'cancel_requested_at',
    'cancel_requested_by', 'cancel_reason', 'result_summary',
))

_RUN_NAME_RE = re.compile(r'^RUN-[0-9]{8}-[0-9]+$')
_SHA256_RE = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)
_EMAIL_RE = re.compile(
    r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
)
_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')
_SENSITIVE_KEY_PARTS = frozenset((
    'access_token', 'token', 'secret', 'password', 'authorization',
    'api_key', 'apikey', 'client_secret', 'refresh_token', 'hmac',
    'payload', 'variables', 'query', 'raw_body', 'headers',
    'email', 'phone', 'address', 'customer', 'line_items',
))
_MAX_JSON_DEPTH = 6
_MAX_JSON_ITEMS = 100
_MAX_CONFIGURATION_BYTES = 8192
_MAX_SUMMARY_CHARS = 2048


def _safe_text(value, limit=_MAX_SUMMARY_CHARS):
    """Return bounded operator text without credentials or obvious PII."""
    if value in (None, False):
        return value
    if not isinstance(value, str):
        value = str(value)
    value = redact(value)
    value = _EMAIL_RE.sub('***', value)
    value = _PHONE_RE.sub('***', value)
    return value[:limit]


def _required_text(value, label, limit):
    value = _safe_text(value, limit)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError('%s cannot be blank.' % label)
    return value.strip()


def _sensitive_key(key):
    key = str(key).lower().replace('-', '_')
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def _safe_json(value, depth=0):
    """Recursively redact and bound JSON-safe metadata.

    Configuration snapshots and result observations are deliberately not raw
    request/response storage.  Rejecting unsupported values and excessive
    shape is safer than stringifying an arbitrary ORM object or silently
    retaining an unbounded payload.
    """
    if depth > _MAX_JSON_DEPTH:
        raise ValidationError('Run metadata is nested too deeply.')
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError('Run metadata cannot contain non-finite numbers.')
        return value
    if isinstance(value, str):
        return _safe_text(value, 512)
    if isinstance(value, dict):
        if len(value) > _MAX_JSON_ITEMS:
            raise ValidationError('Run metadata contains too many keys.')
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError('Run metadata keys must be strings.')
            safe_key = _safe_text(key, 64)
            if safe_key in result:
                raise ValidationError('Run metadata keys must be unique.')
            result[safe_key] = (
                '***' if _sensitive_key(safe_key)
                else _safe_json(item, depth + 1)
            )
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_JSON_ITEMS:
            raise ValidationError('Run metadata contains too many items.')
        return [_safe_json(item, depth + 1) for item in value]
    raise ValidationError('Run metadata must contain JSON-safe values.')


def _bounded_json(value, label, maximum):
    safe = _safe_json(value if value is not None else {})
    if not isinstance(safe, dict):
        raise ValidationError('%s must be a JSON object.' % label)
    try:
        encoded = json.dumps(
            safe, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError('%s must be JSON-safe.' % label) from exc
    if len(encoded.encode('utf-8')) > maximum:
        raise ValidationError('%s is larger than the bounded limit.' % label)
    return safe


def _generation_for_store(store):
    value = getattr(store, 'connection_generation', 0) or 0
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            'The store connection generation must be an integer.'
        ) from exc
    if value < 0:
        raise ValidationError('The store connection generation cannot be negative.')
    return value


def _configuration_generation_for_store(env, store):
    """Read the current V2 settings epoch without creating configuration.

    A legacy store may not have a canonical settings row yet; its additive
    runtime snapshot uses generation zero until the settings service creates
    one.  The V2 claimant itself requires a real settings row, so this
    compatibility default cannot admit work across an absent configuration
    boundary.
    """
    Settings = env['shopify.connector.store.settings'].sudo()
    settings = Settings.search([('store_id', '=', store.id)], limit=1)
    if not settings or 'configuration_generation' not in settings._fields:
        return 0
    value = settings.configuration_generation or 0
    if isinstance(value, bool):
        raise ValidationError(
            'The store configuration generation must be an integer.'
        )
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            'The store configuration generation must be an integer.'
        ) from exc
    if value < 0:
        raise ValidationError(
            'The store configuration generation cannot be negative.'
        )
    return value


def _safe_fingerprint(value):
    if value in (None, False):
        return value
    value = str(value).lower()
    if not _SHA256_RE.match(value):
        raise ValidationError('scope_fingerprint must be a SHA-256 digest.')
    return value
