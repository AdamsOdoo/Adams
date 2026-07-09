import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models import shopify_connector_job_dispatch as dispatch_module
from ..models.shopify_connector_job_dispatch import (
    JobHandlerError,
    RETRY_BASE_DELAY_SECONDS,
    RETRY_JITTER_FRACTION,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY_SECONDS,
    RETRY_MULTIPLIER,
    RETRY_WINDOW_HOURS,
    SAFETY_NET_MAX_ATTEMPTS,
)

# Wall-clock tolerance (seconds) for bound assertions below -- absorbs
# the small, real elapsed time between capturing `before`/`after` and
# the code under test computing `fields.Datetime.now()` itself. Never
# relies on unseeded randomness for a pass/fail result -- every bound
# below is deterministic given the named Decision C constants.
_CLOCK_TOLERANCE_SECONDS = 3


class TestJobRetryScheduling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Job Retry Scheduling Test Store',
            'shop_domain': 'job-retry-scheduling-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']

    def _create_selftest_job(self, state='queued', **extra):
        vals = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        }
        vals.update(extra)
        return self.Job.create(vals)

    def _run_with_handler_error(self, job, error_class, reason='synthetic failure'):
        def _raise(self, job):
            raise JobHandlerError(error_class, reason)
        with patch.object(
            type(self.Dispatch), '_get_handlers',
            lambda self: {'core_dispatch_selftest': _raise},
        ):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()

    def _assert_delay_within_bounds(self, delta_seconds, expected_base):
        lower = expected_base * (1 - RETRY_JITTER_FRACTION) - _CLOCK_TOLERANCE_SECONDS
        upper = expected_base * (1 + RETRY_JITTER_FRACTION) + _CLOCK_TOLERANCE_SECONDS
        self.assertTrue(
            lower <= delta_seconds <= upper,
            'delay %.2fs not within [%.2fs, %.2fs]' % (delta_seconds, lower, upper),
        )

    # ------------------------------------------------------------------
    # Retryable error schedules retry (Decision C defaults).
    # ------------------------------------------------------------------

    def test_throttling_error_schedules_retry_waiting_with_bounded_delay(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        before = fields.Datetime.now()
        self._run_with_handler_error(job, 'shopify_throttling_rate_limit')
        self.assertEqual(job.state, 'retry_waiting')
        self.assertEqual(job.retry_count, 1)
        self.assertEqual(job.error_class, 'shopify_throttling_rate_limit')
        self.assertTrue(job.next_retry_at)
        delta = (job.next_retry_at - before).total_seconds()
        expected_base = RETRY_BASE_DELAY_SECONDS * (RETRY_MULTIPLIER ** 0)
        self._assert_delay_within_bounds(delta, expected_base)

    def test_retry_delay_grows_exponentially_with_attempts(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued', retry_count=3)
        before = fields.Datetime.now()
        self._run_with_handler_error(job, 'concurrency_race_conflict')
        self.assertEqual(job.retry_count, 4)
        delta = (job.next_retry_at - before).total_seconds()
        expected_base = min(
            RETRY_BASE_DELAY_SECONDS * (RETRY_MULTIPLIER ** 3),
            RETRY_MAX_DELAY_SECONDS,
        )
        self._assert_delay_within_bounds(delta, expected_base)

    def test_retry_delay_capped_at_thirty_minutes(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued', retry_count=10)
        before = fields.Datetime.now()
        self._run_with_handler_error(job, 'shopify_temporary_server_network')
        delta = (job.next_retry_at - before).total_seconds()
        self._assert_delay_within_bounds(delta, RETRY_MAX_DELAY_SECONDS)

    def test_retry_delay_is_deterministic_with_patched_jitter(self):
        # Injectable-jitter seam: patching random.uniform makes the
        # exact resulting delay deterministic, avoiding any reliance on
        # unseeded randomness for this particular assertion.
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        before = fields.Datetime.now()
        with patch.object(dispatch_module.random, 'uniform', lambda a, b: 0):
            self._run_with_handler_error(job, 'shopify_throttling_rate_limit')
        delta = (job.next_retry_at - before).total_seconds()
        self.assertTrue(
            RETRY_BASE_DELAY_SECONDS - _CLOCK_TOLERANCE_SECONDS
            <= delta
            <= RETRY_BASE_DELAY_SECONDS + _CLOCK_TOLERANCE_SECONDS
        )

    # ------------------------------------------------------------------
    # Bounded retries: max-attempts / retry-window exhaustion ->
    # failed_final. No infinite retries under any circumstance
    # (DEC-009).
    # ------------------------------------------------------------------

    def test_auto_retry_class_exhausts_max_attempts_to_failed_final(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(
            state='queued', retry_count=RETRY_MAX_ATTEMPTS,
            started_at=fields.Datetime.now(),
        )
        self._run_with_handler_error(job, 'shopify_throttling_rate_limit')
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.error_class, 'shopify_throttling_rate_limit')
        # The job did attempt and fail again -- the exhausted attempt
        # count must be persisted, not left at its pre-attempt value.
        self.assertEqual(job.retry_count, RETRY_MAX_ATTEMPTS + 1)

    def test_auto_retry_class_exceeds_retry_window_to_failed_final(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(
            state='queued', retry_count=1,
            started_at=(
                fields.Datetime.now()
                - timedelta(hours=RETRY_WINDOW_HOURS, minutes=1)
            ),
        )
        self._run_with_handler_error(job, 'shopify_throttling_rate_limit')
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.retry_count, 2)

    def test_unknown_system_error_retries_once_then_fails_final(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        self._run_with_handler_error(job, 'unknown_system_error')
        self.assertEqual(job.state, 'retry_waiting')
        self.assertEqual(job.retry_count, SAFETY_NET_MAX_ATTEMPTS)

        # Make the scheduled retry due, then fail it again -- the
        # single safety-net budget must not grant a second retry.
        job.write({'next_retry_at': fields.Datetime.now() - timedelta(seconds=1)})
        self._run_with_handler_error(job, 'unknown_system_error')
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.retry_count, SAFETY_NET_MAX_ATTEMPTS + 1)

    # ------------------------------------------------------------------
    # Terminal error goes failed_final / failed_retryable /
    # blocked_manual_review as applicable.
    # ------------------------------------------------------------------

    def test_manual_fix_then_retry_classes_go_failed_retryable(self):
        self.store.write({'state': 'connected'})
        for error_class in (
            'shopify_permission_scope_auth', 'shopify_user_errors_validation',
            'odoo_validation_configuration', 'mapping_missing',
            'data_shape_schema_mismatch',
        ):
            job = self._create_selftest_job(state='queued')
            self._run_with_handler_error(job, error_class)
            self.assertEqual(job.state, 'failed_retryable', error_class)
            self.assertFalse(job.manual_review_subreason)
            self.assertTrue(job.finished_at)

    def test_financial_total_mismatch_goes_failed_retryable(self):
        # "Conservative, never silent" (architecture gate §E) -- cannot
        # be blocked_manual_review: financial_total_mismatch is not one
        # of the six manual_review_subreason values, and the job
        # model's own _check_manual_review_subreason_required
        # constraint (unmodified) would reject that combination.
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        self._run_with_handler_error(job, 'financial_total_mismatch')
        self.assertEqual(job.state, 'failed_retryable')

    def test_manual_review_classes_go_blocked_manual_review_with_matching_subreason(self):
        self.store.write({'state': 'connected'})
        for error_class in (
            'ambiguous_match', 'binding_conflict', 'duplicate_risk',
            'destructive_write_guard_blocked', 'inventory_location_missing',
            'fulfillment_notification_confirmation_missing',
        ):
            job = self._create_selftest_job(state='queued')
            self._run_with_handler_error(job, error_class)
            self.assertEqual(job.state, 'blocked_manual_review', error_class)
            self.assertEqual(job.manual_review_subreason, error_class)
            self.assertTrue(job.finished_at)

    def test_generic_exception_from_handler_treated_as_unknown_system_error(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')

        def _raise_plain(self, job):
            raise RuntimeError('unexpected handler bug')

        with patch.object(
            type(self.Dispatch), '_get_handlers',
            lambda self: {'core_dispatch_selftest': _raise_plain},
        ):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'retry_waiting')
        self.assertEqual(job.error_class, 'unknown_system_error')
