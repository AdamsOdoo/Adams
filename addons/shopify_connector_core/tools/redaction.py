import re

SENSITIVE_KEYS = (
    'access_token',
    'token',
    'secret',
    'password',
    'authorization',
    'x-shopify-access-token',
    'api_key',
    'apikey',
    'client_secret',
    'refresh_token',
    'hmac',
)

SENSITIVE_VALUE_PATTERNS = (
    re.compile(r'shpat_[A-Za-z0-9]+'),
    re.compile(r'shprt_[A-Za-z0-9]+'),
)

REDACTED = '***'


def _redact_str(value, extra_secrets):
    for pattern in SENSITIVE_VALUE_PATTERNS:
        value = pattern.sub(REDACTED, value)
    for secret in extra_secrets:
        if secret:
            value = value.replace(secret, REDACTED)
    return value


def _key_is_sensitive(key):
    key = str(key).lower()
    return any(sensitive in key for sensitive in SENSITIVE_KEYS)


def redact(value, extra_secrets=None):
    """Recursively redact sensitive keys/values from str/dict/list/tuple.

    Idempotent, never raises, never mutates its input, and passes any
    other type through unchanged.
    """
    extra_secrets = extra_secrets or ()
    if isinstance(value, str):
        return _redact_str(value, extra_secrets)
    if isinstance(value, dict):
        return {
            key: (REDACTED if _key_is_sensitive(key) else redact(val, extra_secrets))
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        redacted = [redact(item, extra_secrets) for item in value]
        return type(value)(redacted)
    return value
