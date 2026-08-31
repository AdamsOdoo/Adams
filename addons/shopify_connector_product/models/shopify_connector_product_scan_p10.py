"""Claim-fenced P10 product enumeration over the P06 read gateway.

Shopify I/O precedes a short side-cursor commit.  Per-product children remain
explicit legacy-compatibility work until their V2 handler is registered.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import re

from psycopg2 import Error as PsycopgError
from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.runtime.p10_coordinator import (
    ClaimedWork,
    RuntimeBoundaryError,
)
from odoo.addons.shopify_connector_core.runtime.p10_decisions import (
    KNOWN_ERROR_CLASSES,
    RetryObservation,
    decide_retry,
)
from odoo.addons.shopify_connector_core.runtime.contracts import (
    NeedsReview,
    Retryable,
    Succeeded,
)

from .shopify_connector_product_scan import (
    PRODUCT_SCAN_OVERLAP,
    PRODUCT_SCAN_SLICE_PAGES,
)


_PRODUCT_SCAN_HANDLER = 'product_import_scan'
_UNIQUE_VIOLATION_SQLSTATE = '23505'
_UTC = timezone.utc
_MAX_CURSOR_LENGTH = 512
_PRODUCT_GID_RE = re.compile(r'^gid://shopify/Product/[1-9][0-9]*$')
_RFC3339_UTC_RE = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    r'(?:\.\d+)?(?:Z|\+00:00)$'
)
_TERMINAL_JOB_STATES = frozenset((
    'succeeded', 'failed_final', 'skipped', 'cancelled',
))
_AUTO_RETRY_ERROR_CLASSES = frozenset((
    'shopify_throttling_rate_limit',
    'shopify_temporary_server_network',
    'concurrency_race_conflict',
))
_MANUAL_FIX_ERROR_CLASSES = frozenset((
    'shopify_permission_scope_auth',
    'shopify_user_errors_validation',
    'odoo_validation_configuration',
    'mapping_missing',
    'data_shape_schema_mismatch',
    'financial_total_mismatch',
))


def _shape_failure(message):
    return JobHandlerError('data_shape_schema_mismatch', message)


def _aware_utc(value, field_name):
    """Parse one strict Shopify RFC3339 timestamp into an aware UTC value."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 64
        or not _RFC3339_UTC_RE.fullmatch(value)
    ):
        raise _shape_failure(
            'The Shopify product scan returned an invalid %s.' % field_name,
        )
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError) as exc:
        raise _shape_failure(
            'The Shopify product scan returned an invalid %s.' % field_name,
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise _shape_failure(
            'The Shopify product scan returned a non-UTC %s.' % field_name,
        )
    return parsed.astimezone(_UTC)


def _canonical_utc_second(value):
    """Truncate to Odoo's stored precision without moving the upper bound."""
    return value.replace(microsecond=0)


def _db_utc(value, field_name, *, allow_none=False):
    """Validate an Odoo DB datetime, which is stored as naive UTC."""
    if value in (None, False, ''):
        if allow_none:
            return None
        raise _shape_failure(
            'The durable product scan is missing %s.' % field_name,
        )
    if not isinstance(value, datetime):
        raise _shape_failure(
            'The durable product scan returned an invalid %s.' % field_name,
        )
    if value.tzinfo is not None:
        if value.utcoffset() != timedelta(0):
            raise _shape_failure(
                'The durable product scan returned a non-UTC %s.' % field_name,
            )
        value = value.astimezone(_UTC).replace(tzinfo=None)
    return _canonical_utc_second(value)


def _cursor(value, field_name='product scan cursor', *, allow_none=True):
    if value in (None, False, '') and allow_none:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > _MAX_CURSOR_LENGTH
        or value != value.strip()
    ):
        raise _shape_failure(
            'The Shopify product scan returned an invalid %s.' % field_name,
        )
    return value


def _product_gid(value):
    if not isinstance(value, str) or not _PRODUCT_GID_RE.fullmatch(value):
        raise _shape_failure(
            'The Shopify product scan returned an invalid product identity.',
        )
    return value


def _claim_retry_inputs(claim):
    """Validate retry inputs copied under the repository's claim locks."""
    payload = claim.payload
    retry_count = payload.get('retry_count') if hasattr(payload, 'get') else None
    if (
        isinstance(retry_count, bool)
        or not isinstance(retry_count, int)
        or retry_count < 0
    ):
        raise RuntimeBoundaryError(
            'The product scan claim has invalid retry metadata.',
        )
    requested = payload.get('run_requested_at') if hasattr(payload, 'get') else None
    try:
        first_attempt_at = _aware_utc(
            requested, 'run requested timestamp',
        )
    except JobHandlerError as exc:
        raise RuntimeBoundaryError(
            'The product scan claim has invalid run timestamp metadata.',
        ) from exc
    return retry_count, first_attempt_at


def _claim_jitter_fraction(claim):
    """Return stable bounded jitter without persisting a random value."""
    digest = hashlib.sha256(str(claim.claim_token).encode('utf-8')).digest()
    unit = int.from_bytes(digest[:8], 'big') / float((1 << 64) - 1)
    return (unit * 2.0 - 1.0) * 0.20


def _iso(value):
    value = _db_utc(value, 'scan window')
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _range_filter(start, end):
    clauses = ["updated_at:<='%s'" % _iso(end)]
    if start is not None:
        clauses.insert(0, "updated_at:>'%s'" % _iso(start))
    return ' '.join(clauses)


def _max_datetime(*values):
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None


def _is_unique_violation(exc):
    """Return whether ``exc`` is the expected PostgreSQL unique violation.

    ``IntegrityError`` is also raised for check, foreign-key and not-null
    failures.  Those failures must never be interpreted as an idempotency or
    operation-scope race.  Psycopg2 exposes SQLSTATE through ``pgcode``; the
    diagnostic object is retained as a fallback for small test doubles and
    drivers that only populate ``diag.sqlstate``.
    """
    pgcode = getattr(exc, 'pgcode', None)
    if pgcode is not None:
        return pgcode == _UNIQUE_VIOLATION_SQLSTATE
    return (
        getattr(getattr(exc, 'diag', None), 'sqlstate', None)
        == _UNIQUE_VIOLATION_SQLSTATE
    )


def _record_id(value):
    """Read an Odoo relation id while remaining friendly to test doubles."""
    return getattr(value, 'id', value)


def _job_matches_expected(
    job, *, store_id, job_type, res_model, res_id, target_gid,
    payload_hash=None, check_payload=True,
):
    """Check every caller-owned identity field on one candidate job row."""
    if not job:
        return False
    if not (
        _record_id(getattr(job, 'store_id', None)) == store_id
        and getattr(job, 'job_type', None) == job_type
        and getattr(job, 'res_model', None) == res_model
        and getattr(job, 'res_id', None) == res_id
        and getattr(job, 'shopify_target_gid', None) == target_gid
    ):
        return False
    return not check_payload or (
        getattr(job, 'payload_hash', None) == payload_hash
    )


class ShopifyConnectorProductScanP10(models.AbstractModel):
    """Claim-aware bounded product scan execution and local page commits."""

    _name = 'shopify.connector.product.scan.p10'
    _description = 'Shopify Connector P10 Product Scan Runtime'

    @contextmanager
    def _local_transaction(self):
        """Yield a side environment whose commit is one page boundary."""
        cursor = self.env.registry.cursor()
        side_env = api.Environment(
            cursor, SUPERUSER_ID, dict(self.env.context),
        )
        try:
            yield side_env
            side_env.flush_all()
            cursor.commit()
        except Exception:
            cursor.rollback()
            raise
        finally:
            cursor.close()

    @api.model
    def _job_store_settings(self, claim):
        if not isinstance(claim, ClaimedWork):
            raise _shape_failure('The product scan claim is invalid.')
        Job = self.env['shopify.connector.job'].sudo()
        job = Job.browse(claim.job_id).exists()
        if not job or job.job_type != _PRODUCT_SCAN_HANDLER:
            raise ShopifyQuiescedError(
                'The product scan claim no longer owns a scan job.'
            )
        store = self.env['shopify.connector.store'].sudo().browse(
            claim.store_id,
        ).exists()
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', claim.store_id)], limit=1)
        if not store or not settings:
            raise ShopifyQuiescedError(
                'The product scan store settings are no longer available.'
            )
        # Claim admission committed on a different cursor.  Do not let an
        # environment cache from an earlier request supply stale retry count,
        # run identity, generations, or feature flags to the handler.
        job.invalidate_recordset()
        store.invalidate_recordset()
        settings.invalidate_recordset()
        return job, store, settings

    @api.model
    def _read_window(self, settings, generation):
        """Read and validate the durable window without changing it."""
        end = _db_utc(
            settings.product_scan_window_end_at,
            'scan window end',
            allow_none=True,
        )
        if end is None or settings.product_scan_generation != generation:
            return None
        start = _db_utc(
            settings.product_scan_window_start_at,
            'scan window start',
            allow_none=True,
        )
        cursor = _cursor(settings.product_scan_cursor)
        latest = _db_utc(
            settings.product_scan_latest_at,
            'latest product timestamp',
            allow_none=True,
        )
        if start is not None and start > end:
            raise _shape_failure(
                'The durable product scan window has reversed timestamps.',
            )
        if latest is not None and latest > end:
            raise _shape_failure(
                'The durable product scan latest timestamp exceeds its window.',
            )
        page_count = settings.product_scan_page_count
        if (
            isinstance(page_count, bool)
            or not isinstance(page_count, int)
            or page_count < 0
        ):
            raise _shape_failure('The durable product scan page count is invalid.')
        if page_count and cursor is None:
            raise _shape_failure(
                'The durable product scan page count has no continuation cursor.',
            )
        if page_count == 0 and (cursor is not None or latest is not None):
            raise _shape_failure(
                'The durable product scan cursor/latest has no page count.',
            )
        return {
            'start': start,
            'end': end,
            'cursor': cursor,
            'latest': latest,
            'page_count': page_count,
            'generation': generation,
        }

    @api.model
    def _initialize_window(self, claim, job, store):
        """Capture a fixed window in a short claim-proven local transaction."""
        del job, store
        with self._local_transaction() as side_env:
            client = side_env['shopify.connector.api.client']
            client._validate_v2_read_claim_for_update(claim)
            settings = side_env[
                'shopify.connector.store.settings'
            ].sudo().search([('store_id', '=', claim.store_id)], limit=1)
            if not settings:
                raise ShopifyQuiescedError(
                    'The product scan settings row no longer exists.'
                )
            existing = self._read_window(
                settings, claim.expected_generation,
            )
            if existing is not None:
                return existing

            # A generation change invalidates any incomplete old window.  The
            # checkpoint itself is preserved, so a reconnect re-covers the
            # overlap rather than crossing a stale endpoint boundary.
            checkpoint = _db_utc(
                settings.product_last_import_checkpoint_at,
                'product checkpoint',
                allow_none=True,
            )
            start = checkpoint - PRODUCT_SCAN_OVERLAP if checkpoint else None
            observed_now = _canonical_utc_second(
                datetime.now(_UTC),
            ).replace(tzinfo=None)
            end = _max_datetime(observed_now, checkpoint)
            values = {
                'product_scan_window_start_at': start or False,
                'product_scan_window_end_at': end,
                'product_scan_cursor': False,
                'product_scan_latest_at': False,
                'product_scan_page_count': 0,
                'product_scan_generation': claim.expected_generation,
            }
            settings._settings_service_write('_product_scan', values)
            return {
                'start': start,
                'end': end,
                'cursor': None,
                'latest': None,
                'page_count': 0,
                'generation': claim.expected_generation,
            }

    @api.model
    def _admit_legacy_child(self, side_env, store, source, node):
        """Admit one compatible V1 child, distinguishing safe/re-risked hits."""
        Job = side_env['shopify.connector.job'].sudo()
        values = [
            ('store_id', '=', store.id),
            ('job_type', '=', 'product_import_sync'),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', store.id),
            ('shopify_target_gid', '=', node['id']),
        ]
        try:
            with side_env.cr.savepoint():
                child = side_env['shopify.connector.job.enqueue'].enqueue(
                    store,
                    job_source=source,
                    job_type='product_import_sync',
                    payload_hash=node['updatedAt'],
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=node['id'],
                )
            return 'enqueued', child
        except IntegrityError as exc:
            # The savepoint is essential: the following diagnostic search
            # must run in a usable transaction after the unique violation.
            # IntegrityError also covers check/FK/not-null failures; only a
            # PostgreSQL unique violation can be an enqueue race.
            if not _is_unique_violation(exc):
                raise
            same = Job.search(
                values + [('payload_hash', '=', node['updatedAt'])],
                order='id asc', limit=1,
            )
            if same and _job_matches_expected(
                same,
                store_id=store.id,
                job_type='product_import_sync',
                res_model='shopify.connector.store',
                res_id=store.id,
                target_gid=node['id'],
                payload_hash=node['updatedAt'],
            ):
                return 'collided', same
            active = Job.search(
                values + [('state', 'not in', tuple(_TERMINAL_JOB_STATES))],
                order='id asc', limit=1,
            )
            if active and _job_matches_expected(
                active,
                store_id=store.id,
                job_type='product_import_sync',
                res_model='shopify.connector.store',
                res_id=store.id,
                target_gid=node['id'],
                check_payload=False,
            ):
                raise JobHandlerError(
                    'duplicate_risk',
                    'A changed Shopify product already has active import '
                    'work; the scan stopped for operator review.',
                )
            # No exact idempotency winner or changed active-scope winner was
            # found.  This was not a proven duplicate; preserve the database
            # failure for the runtime boundary instead of misclassifying it as
            # a product-data result.
            raise

    @api.model
    def _commit_page(
        self, claim, job, store, window, nodes, *, has_next, end_cursor,
    ):
        """Atomically admit children and advance exactly one page."""
        # A caller normally passes the value returned by ``_read_window`` or
        # ``_initialize_window``.  Normalize the copy anyway: it is the value
        # used for side-cursor equality below, and a caller must not be able to
        # reintroduce subsecond precision between page boundaries.
        window = dict(window)
        window['start'] = _db_utc(
            window.get('start'), 'scan window start', allow_none=True,
        )
        window['end'] = _db_utc(window.get('end'), 'scan window end')
        window['latest'] = _db_utc(
            window.get('latest'), 'latest product timestamp', allow_none=True,
        )
        latest = window['latest']
        for node in nodes:
            if not isinstance(node, dict):
                raise _shape_failure(
                    'The product scan returned a malformed product node.',
                )
            _product_gid(node.get('id'))
            observed_exact = _aware_utc(
                node.get('updatedAt'), 'product updatedAt',
            ).replace(tzinfo=None)
            if observed_exact > window['end']:
                raise _shape_failure(
                    'The product scan returned a product outside its fixed '
                    'time window; the page was not committed.',
                )
            observed = _canonical_utc_second(observed_exact)
            latest = _max_datetime(latest, observed)

        if has_next:
            end_cursor = _cursor(end_cursor, 'next product scan cursor', allow_none=False)
            if end_cursor == window['cursor']:
                raise _shape_failure(
                    'The product scan cursor did not make progress.',
                )
        elif end_cursor is not None:
            raise _shape_failure(
                'The terminal product scan page carried a cursor.',
            )

        counts = {
            'enumerated': len(nodes),
            'enqueued': 0,
            'collided': 0,
        }
        with self._local_transaction() as side_env:
            client = side_env['shopify.connector.api.client']
            client._validate_v2_read_claim_for_update(claim)
            side_store = side_env['shopify.connector.store'].sudo().browse(
                store.id,
            ).exists()
            settings = side_env[
                'shopify.connector.store.settings'
            ].sudo().search([('store_id', '=', store.id)], limit=1)
            if not side_store or not settings:
                raise ShopifyQuiescedError(
                    'The product scan local page owner disappeared.',
                )
            current = self._read_window(
                settings, claim.expected_generation,
            )
            if current is None:
                raise JobHandlerError(
                    'concurrency_race_conflict',
                    'The product scan window changed before its page commit.',
                )
            if any(current[key] != window[key] for key in (
                'start', 'end', 'cursor', 'latest', 'page_count',
            )):
                raise JobHandlerError(
                    'concurrency_race_conflict',
                    'The product scan checkpoint changed before its page '
                    'could be committed.',
                )

            for node in nodes:
                outcome, _child = self._admit_legacy_child(
                    side_env, side_store, job.job_source, node,
                )
                counts[outcome] += 1

            next_page_count = current['page_count'] + 1
            if has_next:
                settings._settings_service_write('_product_scan', {
                    'product_scan_cursor': end_cursor,
                    'product_scan_latest_at': latest or False,
                    'product_scan_page_count': next_page_count,
                })
                continuation = True
            else:
                checkpoint = _db_utc(
                    settings.product_last_import_checkpoint_at,
                    'product checkpoint',
                    allow_none=True,
                )
                # A regressed wall clock must never move durable progress
                # backwards.  Keep the greatest proven boundary: the prior
                # checkpoint, the latest observed product, or the fixed window
                # end when the page is empty.
                next_checkpoint = _max_datetime(
                    checkpoint, latest, current['end'],
                )
                settings._settings_service_write('_product_scan', {
                    'product_last_import_checkpoint_at': next_checkpoint,
                    'product_last_import_success_at': current['end'],
                    'product_scan_window_start_at': False,
                    'product_scan_window_end_at': False,
                    'product_scan_cursor': False,
                    'product_scan_latest_at': False,
                    'product_scan_page_count': 0,
                    'product_scan_generation': 0,
                })
                continuation = False
        counts['pages'] = 1
        counts['continuation'] = continuation
        return counts

    @api.model
    def _retry_or_review(self, claim, error_class):
        """Preserve retry policy using only the immutable claim snapshot."""
        if error_class not in KNOWN_ERROR_CLASSES:
            return NeedsReview(
                'unknown_error_class',
                'The product scan returned an unregistered error class.',
                error_class='unknown_system_error',
            )
        if error_class in _MANUAL_FIX_ERROR_CLASSES:
            return NeedsReview(
                error_class,
                'Resolve the product scan issue, then retry the run.',
                error_class=error_class,
            )
        if error_class not in _AUTO_RETRY_ERROR_CLASSES:
            return NeedsReview(
                error_class,
                'Review the product scan evidence before retrying.',
                error_class=error_class,
            )
        retry_count, first = _claim_retry_inputs(claim)
        now = datetime.now(_UTC)
        decision = decide_retry(RetryObservation(
            error_class=error_class,
            remote_outcome='failed_clean',
            retry_count=retry_count,
            first_attempt_at=first,
            now=now,
            jitter_fraction=_claim_jitter_fraction(claim),
        ))
        if decision.action != 'retry':
            return NeedsReview(
                decision.reason_code,
                'Review the product scan retry budget before retrying.',
                error_class=error_class,
            )
        return Retryable(
            error_class,
            decision.retry_at,
            {
                'retry_number': decision.retry_number,
                'delay_seconds': decision.delay_seconds,
                'jitter_fraction': decision.jitter_fraction,
                'product_scan_error': error_class,
            },
        )

    @api.model
    def _result_for_failure(self, claim, exc):
        if isinstance(exc, JobHandlerError):
            return self._retry_or_review(claim, exc.error_class)
        if isinstance(exc, ShopifyClientError):
            return self._retry_or_review(claim, exc.error_class)
        raise RuntimeBoundaryError(
            'The product scan failure was not a classified handler error.',
        )

    @api.model
    def handle_claim(self, claim):
        """Execute at most ten network pages for one immutable claim."""
        job, store, settings = self._job_store_settings(claim)
        if not settings.product_domain_enabled:
            return NeedsReview(
                'odoo_validation_configuration',
                'Enable the product domain before running a product scan.',
                error_class='odoo_validation_configuration',
            )
        if settings.product_first_sync_source == 'odoo_source':
            return NeedsReview(
                'odoo_validation_configuration',
                'This store treats Odoo as the product source; no Shopify '
                'product scan was performed.',
                error_class='odoo_validation_configuration',
            )

        try:
            window = self._read_window(
                settings, claim.expected_generation,
            )
            if window is None:
                window = self._initialize_window(claim, job, store)
            seen_cursors = set()
            seen_gids = set()
            total = {
                'enumerated': 0,
                'enqueued': 0,
                'collided': 0,
                'pages': 0,
            }
            for _page_index in range(PRODUCT_SCAN_SLICE_PAGES):
                cursor = _cursor(window['cursor'])
                if cursor is not None:
                    seen_cursors.add(cursor)
                page = self.env[
                    'shopify.connector.product.scan'
                ]._read_product_scan_page(
                    job,
                    store,
                    query_filter=_range_filter(window['start'], window['end']),
                    cursor=cursor,
                    page_limit=PRODUCT_SCAN_SLICE_PAGES,
                    seen_cursors=seen_cursors,
                    seen_gids=seen_gids,
                    claim=claim,
                )
                page = dict(page or {})
                nodes = page.get('nodes')
                has_next = page.get('has_next')
                if not isinstance(nodes, list) or not isinstance(has_next, bool):
                    raise _shape_failure(
                        'The product scan gateway returned invalid page metadata.',
                    )
                page_counts = self._commit_page(
                    claim,
                    job,
                    store,
                    window,
                    nodes,
                    has_next=has_next,
                    end_cursor=page.get('end_cursor'),
                )
                for key in ('enumerated', 'enqueued', 'collided', 'pages'):
                    total[key] += page_counts.get(key, 0)
                continuation = bool(page_counts['continuation'])
                total['continuation'] = continuation
                if not continuation:
                    break
                # The local transaction committed the next cursor/window. Use
                # the in-memory page result for the next network read, then
                # refresh settings only at the next iteration boundary.
                window = dict(window)
                window['cursor'] = page['end_cursor']
                window['latest'] = _max_datetime(
                    window['latest'],
                    *(_canonical_utc_second(
                        _aware_utc(node.get('updatedAt'), 'product updatedAt'),
                    ).replace(tzinfo=None) for node in nodes),
                )
                window['page_count'] += 1
            return Succeeded({
                'pages_processed': total['pages'],
                'products_enumerated': total['enumerated'],
                'children_enqueued': total['enqueued'],
                'children_coalesced': total['collided'],
                'continuation': bool(total.get('continuation')),
                'child_runtime': 'legacy_compatibility',
            })
        except (PsycopgError, ShopifyQuiescedError, RuntimeBoundaryError):
            # A database failure or a lost claim is not a product-data result.
            # Let the runtime boundary roll back and record the infrastructure
            # failure; translating it here could make an uncommitted page look
            # safely retryable and would hide ownership loss.
            raise
        except (JobHandlerError, ShopifyClientError) as exc:
            # These are handler-boundary outcomes.  Convert them only after the
            # page transaction has unwound, preserving the source error class.
            return self._result_for_failure(claim, exc)


__all__ = ['ShopifyConnectorProductScanP10']
