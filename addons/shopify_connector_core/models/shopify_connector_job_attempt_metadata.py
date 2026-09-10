"""Bounded, redacted evidence helpers for execution attempts.

This module intentionally contains no model declaration.  Keeping the
validation helpers separate leaves the attempt model room for lifecycle and
scope guards while preserving their historical module-level imports through
the re-export in ``shopify_connector_job_attempt``.
"""

import json
import math
import re

from odoo.exceptions import ValidationError

from ..tools.redaction import redact


_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-'
    r'[0-9a-f]{12}$|^[0-9a-f]{32}$',
    re.IGNORECASE,
)
_DIGEST_RE = re.compile(r'^[0-9a-f]{64}$', re.IGNORECASE)
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
_MAX_OBSERVATION_BYTES = 8192
_MAX_TEXT_CHARS = 2048


def _safe_text(value, limit=_MAX_TEXT_CHARS):
    if value in (None, False):
        return value
    if not isinstance(value, str):
        value = str(value)
    value = redact(value)
    value = _EMAIL_RE.sub('***', value)
    value = _PHONE_RE.sub('***', value)
    return value[:limit]


def _sensitive_key(key):
    key = str(key).lower().replace('-', '_')
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def _safe_json(value, depth=0):
    if depth > _MAX_JSON_DEPTH:
        raise ValidationError('Attempt observations are nested too deeply.')
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(
                'Attempt observations cannot contain non-finite numbers.'
            )
        return value
    if isinstance(value, str):
        return _safe_text(value, 512)
    if isinstance(value, dict):
        if len(value) > _MAX_JSON_ITEMS:
            raise ValidationError('Attempt observations contain too many keys.')
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError('Attempt observation keys must be strings.')
            safe_key = _safe_text(key, 64)
            if safe_key in result:
                raise ValidationError('Attempt observation keys must be unique.')
            result[safe_key] = (
                '***' if _sensitive_key(safe_key)
                else _safe_json(item, depth + 1)
            )
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_JSON_ITEMS:
            raise ValidationError(
                'Attempt observations contain too many items.'
            )
        return [_safe_json(item, depth + 1) for item in value]
    raise ValidationError('Attempt observations must be JSON-safe.')


def _bounded_json(value):
    safe = _safe_json(value if value is not None else {})
    if not isinstance(safe, dict):
        raise ValidationError('Attempt observations must be a JSON object.')
    try:
        encoded = json.dumps(
            safe, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError('Attempt observations must be JSON-safe.') from exc
    if len(encoded.encode('utf-8')) > _MAX_OBSERVATION_BYTES:
        raise ValidationError('Attempt observations exceed the bounded limit.')
    return safe


def _safe_digest(value, label):
    if value in (None, False):
        return value
    value = str(value).lower()
    if not _DIGEST_RE.match(value):
        raise ValidationError('%s must be a SHA-256 digest.' % label)
    return value


def _uuid_token(value, label):
    value = str(value)
    if not _UUID_RE.match(value):
        raise ValidationError('%s must be an opaque UUID.' % label)
    return value


def _non_negative_number(value, label):
    """Return a finite non-negative number, rejecting numeric strings."""
    if value is None or value is False:
        return value
    if type(value) not in (int, float):
        raise ValidationError('%s must be numeric.' % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValidationError('%s must be finite.' % label)
    if value < 0:
        raise ValidationError('%s cannot be negative.' % label)
    return value
