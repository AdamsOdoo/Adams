import ast
import uuid
from pathlib import Path

from odoo.tests.common import TransactionCase


class TestFulfillmentLifecycle(TransactionCase):
    """Uninstall/ondelete behaviour: the job-type sink retypes fulfillment jobs
    to historic_domain_job; the DEDICATED trigger-origin callable normalizes the
    removed fulfillment_tracking_change value to the core
    fulfillment_picking_validation value with exactly one provenance audit,
    never clearing it while job_source='odoo_event' and never changing
    job_source. Zero residue; order-independent with the job-type sink."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })

    def _job(self, job_type, job_source='odoo_event', trigger_origin=False, state='queued'):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': job_source,
            'trigger_origin': trigger_origin,
            'job_type': job_type,
            'state': state,
            'payload_hash': uuid.uuid4().hex,
        })

    def test_job_type_sink_retypes_to_historic(self):
        # odoo_event jobs require a trigger_origin (core constraint); supply the
        # valid core value explicitly.
        job = self._job(
            'fulfillment_create',
            trigger_origin='fulfillment_picking_validation',
        )
        job._reassign_to_historic_job_type()
        job.invalidate_recordset()
        self.assertEqual(job.job_type, 'historic_domain_job')
        self.assertEqual(job.original_job_type, 'fulfillment_create')

    def test_trigger_origin_normalized_with_single_audit(self):
        job = self._job(
            'fulfillment_tracking_admission',
            trigger_origin='fulfillment_tracking_change',
        )
        before = self.JobLog.search_count([('job_id', '=', job.id)])
        job._normalize_tracking_change_trigger_origin_on_uninstall()
        job.invalidate_recordset()
        # Removed value normalized to the core value; job_source unchanged.
        self.assertEqual(job.trigger_origin, 'fulfillment_picking_validation')
        self.assertEqual(job.job_source, 'odoo_event')
        # Exactly one provenance audit entry.
        after = self.JobLog.search_count([('job_id', '=', job.id)])
        self.assertEqual(after - before, 1)

    def test_no_removed_trigger_origin_value_survives(self):
        jobs = self.Job.browse()
        for state in ('queued', 'running'):
            jobs |= self._job(
                'fulfillment_tracking_update',
                trigger_origin='fulfillment_tracking_change', state=state,
            )
        jobs._normalize_tracking_change_trigger_origin_on_uninstall()
        residue = self.Job.search_count([
            ('trigger_origin', '=', 'fulfillment_tracking_change'),
        ])
        self.assertEqual(residue, 0)

    def test_constraint_stays_satisfied_after_normalization(self):
        job = self._job(
            'fulfillment_tracking_admission',
            trigger_origin='fulfillment_tracking_change',
        )
        job._normalize_tracking_change_trigger_origin_on_uninstall()
        job.invalidate_recordset()
        # odoo_event still carries a (normalized) trigger origin -> constraint ok.
        job._check_trigger_origin_required()

    def test_order_independent_with_job_type_sink(self):
        # trigger-origin normalization first, then job-type sink.
        job_a = self._job(
            'fulfillment_tracking_update',
            trigger_origin='fulfillment_tracking_change',
        )
        job_a._normalize_tracking_change_trigger_origin_on_uninstall()
        job_a._reassign_to_historic_job_type()
        job_a.invalidate_recordset()
        self.assertEqual(job_a.job_type, 'historic_domain_job')
        self.assertEqual(job_a.trigger_origin, 'fulfillment_picking_validation')
        # job-type sink first, then trigger-origin normalization.
        job_b = self._job(
            'fulfillment_tracking_update',
            trigger_origin='fulfillment_tracking_change',
        )
        job_b._reassign_to_historic_job_type()
        job_b._normalize_tracking_change_trigger_origin_on_uninstall()
        job_b.invalidate_recordset()
        self.assertEqual(job_b.job_type, 'historic_domain_job')
        self.assertEqual(job_b.trigger_origin, 'fulfillment_picking_validation')

    def test_ondelete_registration_uses_dedicated_callable(self):
        source = (
            Path(__file__).resolve().parents[1]
            / 'models' / 'shopify_connector_job.py'
        ).read_text('utf-8')
        # The trigger-origin ondelete uses the dedicated normalization callable,
        # NOT the job-type sink.
        self.assertIn(
            '_normalize_tracking_change_trigger_origin_on_uninstall', source,
        )
        tree = ast.parse(source)
        # The dedicated callable exists as a method and contains no unlink.
        method = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
            and n.name == '_normalize_tracking_change_trigger_origin_on_uninstall'
        )
        self.assertFalse(any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == 'unlink'
            for c in ast.walk(method)
        ))

    def test_all_ten_job_types_have_historic_ondelete(self):
        from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_job import (  # noqa: E501
            FULFILLMENT_JOB_TYPES,
        )
        field = self.Job._fields['job_type']
        for job_type in FULFILLMENT_JOB_TYPES:
            self.assertIn(job_type, field.ondelete)
