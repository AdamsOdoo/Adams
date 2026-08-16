"""The apply -> first-step hand-off, driven through the real dispatcher.

Why this file exists at all. `operation_scope_key` is computed from
`store_id | res_model | res_id | shopify_target_gid` and deliberately
excludes `job_type`, and `_store_operation_scope_key_uniq` enforces
`UNIQUE(store_id, operation_scope_key)`. The apply job and the step it hands
off to agree on all four components, so their keys are byte-identical. The
hand-off is therefore only legal if the parent has released the key -- i.e.
reached a terminal state AND been flushed -- before the child is created.

Every other apply test calls `_handle_product_export_apply` directly and
never flushes, which is precisely the shape that cannot observe this: the
child is created inside the same uncommitted transaction as a parent whose
recomputed key was never written. These tests drive `_dispatch_one` and
flush explicitly, which is what production does.
"""

from unittest.mock import patch

from odoo.tests.common import tagged

from ..models.shopify_connector_product_export_service import (
    JOB_TYPE_APPLY,
    JOB_TYPE_CREATE,
    JOB_TYPE_UPDATE,
)
from .common import ExportCase, FakeSendResponse, PRODUCT_GID
from .test_export_preview_guard import _product_read_body
from odoo.tools import mute_logger

TERMINAL = ('succeeded', 'failed_final', 'skipped', 'cancelled')


@tagged('post_install', '-at_install')
class TestExportApplyHandoff(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template(variant_gid=None)
        self.Job = self.env['shopify.connector.job']
        self.Dispatch = self.env['shopify.connector.job.dispatch']

    def _confirmed_preview(self):
        preview = self.make_preview(
            binding=self.binding, state='confirmed',
            remote_updated_at='2026-07-26T00:00:00Z',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        return preview

    def _apply_job(self, preview):
        return self.make_job(
            JOB_TYPE_APPLY, preview._name, preview.id, PRODUCT_GID,
        )

    def _dispatch(self, job):
        """Drive the real dispatcher, then flush like production does."""
        response = FakeSendResponse(_product_read_body())
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Dispatch._dispatch_one(job)
            self.env.flush_all()

    # ------------------------------------------------------------------
    # The hand-off completes
    # ------------------------------------------------------------------

    def test_apply_hands_off_to_its_first_step_through_the_dispatcher(self):
        preview = self._confirmed_preview()
        job = self._apply_job(preview)
        self.env.flush_all()
        # Precondition: the parent really does hold the contested key.
        self.assertTrue(job.operation_scope_key)

        self._dispatch(job)

        job.invalidate_recordset()
        child = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_UPDATE),
        ])
        self.assertEqual(len(child), 1, 'the first step must be enqueued')
        self.assertEqual(child.state, 'queued')
        # The parent released the key; the child now holds it. Both halves
        # matter: a terminal parent that was never flushed still owns the row.
        self.assertIn(job.state, TERMINAL)
        self.assertFalse(job.operation_scope_key)
        self.assertEqual(
            child.operation_scope_key,
            '%s|%s|%s|%s' % (
                self.store.id, preview._name, preview.id, PRODUCT_GID,
            ),
        )
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'applying')

    def test_the_parent_is_transitioned_exactly_once(self):
        """The handler terminalises; `_invoke_handler` must not do it again."""
        preview = self._confirmed_preview()
        job = self._apply_job(preview)
        self._dispatch(job)

        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        transitions = self.env['shopify.connector.job.log'].search([
            ('job_id', '=', job.id),
            ('to_state', '=', 'succeeded'),
        ])
        self.assertEqual(
            len(transitions), 1,
            'a second write to succeeded would mean the dispatcher '
            're-finalised a job the handler had already terminalised',
        )

    # ------------------------------------------------------------------
    # Uniqueness is not weakened
    # ------------------------------------------------------------------

    def _rival_job(self, preview, job_type):
        """A job on the SAME scope but a different idempotency key.

        `make_job` derives `payload_hash` from `job_type` and `res_id`, so a
        second apply would collide on `_store_idempotency_key_uniq` first and
        prove nothing about the scope key. Varying `job_type` keeps the four
        scope components identical while making the idempotency key differ,
        so only the scope constraint can fire.
        """
        return self.make_job(job_type, preview._name, preview.id, PRODUCT_GID)

    @mute_logger('odoo.sql_db')
    def test_a_second_live_job_for_the_same_target_is_still_refused(self):
        """Releasing the key on hand-off must not open the scope generally."""
        preview = self._confirmed_preview()
        self._apply_job(preview)
        self.env.flush_all()
        with self.assertRaises(Exception) as caught:
            self._rival_job(preview, JOB_TYPE_UPDATE)
            self.env.flush_all()
        self.assertIn('operation_scope_key', str(caught.exception))

    @mute_logger('odoo.sql_db')
    def test_the_child_holds_the_scope_against_a_further_duplicate(self):
        preview = self._confirmed_preview()
        job = self._apply_job(preview)
        self._dispatch(job)
        # The child now owns the scope, so another job on the same target
        # must still be refused rather than racing it.
        with self.assertRaises(Exception) as caught:
            self._rival_job(preview, JOB_TYPE_CREATE)
            self.env.flush_all()
        self.assertIn('operation_scope_key', str(caught.exception))

    # ------------------------------------------------------------------
    # Failure leaves nothing half-applied
    # ------------------------------------------------------------------

    def test_a_failed_handoff_does_not_strand_a_succeeded_parent(self):
        """If the child cannot be created, the parent must not stay green.

        The terminalisation and the child creation are one unit of work: a
        parent recorded `succeeded` with no step behind it would look like a
        completed apply that silently exported nothing.
        """
        preview = self._confirmed_preview()
        job = self._apply_job(preview)

        Service = type(self.env['shopify.connector.product.export.service'])
        boom = patch.object(
            Service, '_enqueue_step',
            side_effect=ValueError('child creation refused'),
        )
        with boom:
            self._dispatch(job)

        job.invalidate_recordset()
        children = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_UPDATE),
        ])
        self.assertFalse(children, 'no step may survive a failed hand-off')
        self.assertNotEqual(
            job.state, 'succeeded',
            'a parent that failed to hand off must not read as succeeded',
        )
