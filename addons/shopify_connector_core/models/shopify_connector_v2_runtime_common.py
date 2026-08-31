"""Shared, framework-light helpers for the V2 runtime adapters.

The claim/finalize repository and stale-owner repository are separate modules
so each remains reviewable.  This module contains only their common constants,
validation and redaction helpers; it owns no ORM model or database operation.
"""

from datetime import timedelta, timezone
import re

from ..domain.immutability import to_plain
from ..runtime.p10_coordinator import RuntimeBoundaryError
from ..runtime.p10_decisions import KNOWN_ERROR_CLASSES
from ..tools.redaction import redact
from .shopify_connector_job import MANUAL_REVIEW_SUBREASON_SELECTION


V2_RUNTIME_MODE = 'read_only'
V2_MAX_CLAIM_BATCH = 100
_UTC = timezone.utc
_ACTIVE_RUN_STATES = ('admitted', 'running', 'waiting')
_TERMINAL_JOB_STATES = ('succeeded', 'failed_final', 'skipped', 'cancelled')
_ACTIVE_ATTEMPT_OUTCOMES = ('claimed', 'running')
_MANUAL_REVIEW_SUBREASONS = frozenset(
    value for value, _label in MANUAL_REVIEW_SUBREASON_SELECTION
)
_GENERATION_ERROR_CLASS = 'store_identity_mismatch'
_GENERATION_SUBREASON = 'store_identity_mismatch'
_CONTRACT_ERROR_CLASS = 'unknown_system_error'
_CONTRACT_SUBREASON = 'idempotency_contract_violation'
_TRANSITION_MESSAGE_LIMIT = 2048
_EMAIL_RE = re.compile(
    r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
)
_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')


class V2RuntimeClaimLost(RuntimeBoundaryError):
    """The claim token no longer owns the job at finalization."""


def _utc(value):
    from datetime import datetime
    if not isinstance(value, datetime):
        raise TypeError('runtime timestamps must be datetime values')
    if value.tzinfo is None:
        return value.replace(tzinfo=_UTC)
    if value.utcoffset() != timedelta(0):
        raise ValueError('runtime timestamps must be UTC')
    return value


def _db_datetime(value):
    """Convert an aware UTC timestamp to Odoo's naive UTC DB value."""
    return _utc(value).replace(tzinfo=None)


def _positive_limit(value, maximum=V2_MAX_CLAIM_BATCH):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError('runtime batch limit must be an integer')
    if not 0 < value <= maximum:
        raise ValueError(
            'runtime batch limit must be between 1 and %d' % maximum
        )
    return value


def _worker(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('worker_ref must be non-empty')
    value = value.strip()
    if len(value) > 128:
        raise ValueError('worker_ref is too long')
    return value


def _safe_observations(result):
    observations = getattr(result, 'observations', {}) or {}
    plain = to_plain(observations)
    if not isinstance(plain, dict):
        return {'observation_shape': 'non_object'}
    return dict(plain)


def _safe_error_class(value, default=_CONTRACT_ERROR_CLASS):
    if isinstance(value, str) and value in KNOWN_ERROR_CLASSES:
        return value
    return default


def _safe_transition_message(value, fallback):
    """Bound handler-derived text before it reaches job-log storage."""
    if not isinstance(value, str):
        return fallback
    safe = redact(value)
    safe = _EMAIL_RE.sub('***', safe)
    safe = _PHONE_RE.sub('***', safe)
    safe = safe[:_TRANSITION_MESSAGE_LIMIT].strip()
    return safe or fallback


def _manual_reason(reason_code):
    """Map arbitrary read-contract reasons into the existing job vocabulary."""
    if isinstance(reason_code, str) and reason_code in _MANUAL_REVIEW_SUBREASONS:
        return reason_code, reason_code
    return _CONTRACT_ERROR_CLASS, _CONTRACT_SUBREASON


def _owner_cleanup():
    return {
        'current_attempt_token': False,
        'owner_worker_ref': False,
        'running_since': False,
        'reconciliation_pending_until': False,
    }


__all__ = [
    'V2_MAX_CLAIM_BATCH',
    'V2_RUNTIME_MODE',
    'V2RuntimeClaimLost',
    '_ACTIVE_ATTEMPT_OUTCOMES',
    '_ACTIVE_RUN_STATES',
    '_CONTRACT_ERROR_CLASS',
    '_CONTRACT_SUBREASON',
    '_GENERATION_ERROR_CLASS',
    '_GENERATION_SUBREASON',
    '_TRANSITION_MESSAGE_LIMIT',
    '_db_datetime',
    '_manual_reason',
    '_owner_cleanup',
    '_positive_limit',
    '_safe_error_class',
    '_safe_observations',
    '_safe_transition_message',
    '_utc',
    '_worker',
]
