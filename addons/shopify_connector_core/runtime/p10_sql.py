"""Pure SQL statement builders for the bounded P10 claim path.

The Odoo adapter owns execution and row persistence; this module owns only
the deterministic statement text and parameter order.  Keeping construction
framework-free makes the most failure-prone part of the claim boundary
testable without a live Odoo registry or PostgreSQL server.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..domain.runtime_modes import runtime_modes_including


_UTC = timedelta(0)
_READ_ONLY_MODES = runtime_modes_including("read_only")


def _utc_db_value(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("claim time must be a datetime")
    if value.tzinfo is None or value.utcoffset() != _UTC:
        raise ValueError("claim time must be timezone-aware UTC")
    return value.replace(tzinfo=None)


def build_claim_statement(
    now: datetime,
    company_ids: tuple[int, ...],
    limit: int,
) -> tuple[str, tuple[Any, ...]]:
    """Build one bounded V2 claim statement and its ordered parameters.

    The SQL parameter order is deliberately returned with the statement:
    four due/reconciliation timestamps, the cumulative-mode tuple, the company
    tuple from the WHERE clause, the aging clock used by ``ORDER BY``, and the
    final row limit.
    Never reorder this tuple without changing the SQL text at the same time.
    """
    now_value = _utc_db_value(now)
    if (
        not isinstance(company_ids, tuple)
        or not company_ids
        or any(
            isinstance(company_id, bool)
            or not isinstance(company_id, int)
            or company_id <= 0
            for company_id in company_ids
        )
    ):
        raise ValueError("company_ids must be a non-empty tuple of IDs")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    lane_rank = (
        "CASE j.lane "
        "WHEN 'safety_verification' THEN 0 "
        "WHEN 'interactive' THEN 1 "
        "WHEN 'webhook' THEN 2 "
        "WHEN 'odoo_event' THEN 3 "
        "WHEN 'scheduled' THEN 4 "
        "WHEN 'reconciliation' THEN 5 END"
    )
    effective_rank = (
        "CASE WHEN j.lane = 'safety_verification' THEN 0 ELSE "
        "GREATEST(1, (%s) - FLOOR(EXTRACT(EPOCH FROM "
        "(%s::timestamp - j.available_at)) / 900)::integer) END"
        % (lane_rank, '%s')
    )
    query = f"""
        SELECT j.id
          FROM shopify_connector_job j
          JOIN shopify_connector_run r
            ON r.id = j.run_id AND r.store_id = j.store_id
          JOIN shopify_connector_store s
            ON s.id = j.store_id AND s.id = r.store_id
          JOIN shopify_connector_store_settings ss
            ON ss.store_id = s.id
          LEFT JOIN shopify_connector_job dep
            ON dep.id = j.blocked_by_job_id
         WHERE j.run_id IS NOT NULL
           AND j.state IN ('queued', 'retry_waiting')
           AND j.available_at IS NOT NULL
           AND j.available_at <= %s
           AND (
                j.state = 'queued'
                OR (
                    j.state = 'retry_waiting'
                    AND j.next_retry_at IS NOT NULL
                    AND j.next_retry_at <= %s
                )
           )
           AND COALESCE(j.reconciliation_pending_until, %s) <= %s
           AND j.current_attempt_token IS NULL
           AND j.owner_worker_ref IS NULL
           AND j.running_since IS NULL
           AND j.lane IS NOT NULL
           AND j.mutation_attempt_id IS NULL
           AND r.state IN ('admitted', 'running', 'waiting')
           AND r.cancel_requested_at IS NULL
           AND s.state = 'connected'
           AND ss.v2_runtime_mode IN %s
           AND j.company_id IS NOT NULL
           AND j.company_id = s.company_id
           AND r.company_id = s.company_id
           AND ss.company_id = s.company_id
           AND s.company_id IN %s
           AND j.expected_connection_generation = s.connection_generation
           AND r.expected_connection_generation = s.connection_generation
           AND j.expected_configuration_generation =
               ss.configuration_generation
           AND r.expected_configuration_generation =
               ss.configuration_generation
           AND (
                j.blocked_by_job_id IS NULL
                OR dep.state IN ('succeeded', 'skipped')
           )
           AND NOT EXISTS (
                SELECT 1
                  FROM shopify_connector_job_attempt active_attempt
                 WHERE active_attempt.job_id = j.id
                   AND active_attempt.outcome IN ('claimed', 'running')
           )
         ORDER BY {effective_rank}, j.available_at, j.lane_priority, j.id
         LIMIT %s
         FOR UPDATE OF j, r, s, ss SKIP LOCKED
    """
    params = (
        now_value,
        now_value,
        now_value,
        now_value,
        _READ_ONLY_MODES,
        company_ids,
        now_value,
        limit,
    )
    return query, params


__all__ = ["build_claim_statement"]
