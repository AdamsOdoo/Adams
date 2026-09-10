"""Shared helpers and run projection for the V2 runtime adapters.

The claim/finalize and stale-owner repositories share constants, validation,
redaction and the locked-job run projection boundary.  The projection executes
inside the caller's transaction; this module owns no ORM model or commit.
"""

from datetime import timedelta, timezone
import re

from odoo import fields

from ..domain.immutability import to_plain
from ..domain.runtime_modes import runtime_mode_includes, runtime_modes_including
from ..runtime.p10_coordinator import RuntimeBoundaryError
from ..runtime.p10_decisions import KNOWN_ERROR_CLASSES, project_run_state
from ..tools.redaction import redact
from .shopify_connector_job import MANUAL_REVIEW_SUBREASON_SELECTION


V2_RUNTIME_MODE = 'read_only'
V2_READ_ONLY_RUNTIME_MODES = runtime_modes_including(V2_RUNTIME_MODE)
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
    'V2_READ_ONLY_RUNTIME_MODES',
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
    'runtime_mode_includes',
]


def refresh_run_state(side_env, run, *, changed_job):
    """Project a locked run after flushing its already-locked changed child.

    Both finalization and stale recovery call this inside their short side
    transaction.  The caller owns job-before-run locks and the commit boundary.
    """
    if not run or not run.exists() or run.state in (
        'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
    ):
        return
    # Every caller owns this job lock before the run lock.  ORM writes
    # remain deferred until flush; raw SQL would otherwise project the
    # preceding state and persist a running run with terminal children.
    # Request the changed state explicitly.  Odoo may also flush other dirty
    # jobs: safety relies on the fresh side environment containing only the
    # finalizer's locked job (plus newly admitted continuation jobs), or the
    # stale sweep's prelocked batch.  Do not dirty unlocked sibling jobs in
    # these transactions; that would invert job-before-run lock ordering.
    changed_job.flush_recordset(['state'])
    side_env.cr.execute(
        """
            SELECT state, COUNT(*)
              FROM shopify_connector_job
             WHERE run_id = %s
             GROUP BY state
        """,
        [run.id],
    )
    counts = {state: int(count) for state, count in side_env.cr.fetchall()}
    target = project_run_state(
        counts, cancel_requested=bool(run.cancel_requested_at),
    )
    if target == run.state:
        return
    if target in (
        'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
    ):
        run._finish_service(target, finished_at=fields.Datetime.now())
    else:
        run._transition_service(target)
