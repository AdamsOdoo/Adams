import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (  # noqa: E501
    FulfillmentReadError,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_job import (
    JOB_TYPE_CREATE,
    JOB_TYPE_MODE_SWITCH_SCAN,
    JOB_TYPE_MODE2_EVALUATION,
    JOB_TYPE_TRACKING_UPDATE,
    TRIGGER_ORIGIN_PICKING,
)


class TestFulfillmentModeSwitch(TransactionCase):
    """The Mode 1 <-> Mode 2 switch state machine on store settings (Modes §6).

    Covers the admin-only actions and the switch-scan handler:
    - action_start_mode2_switch: sets switch_in_progress + a nonce and enqueues
      a mode-switch scan; idempotent no-op when already Mode 2;
    - action_rollback_to_mode1: returns to Mode 1, cancels in-flight Mode 2
      evaluations back to cancelled, but LEAVES in-flight Layer 2
      create/tracking/reconcile mutation jobs untouched;
    - both actions are Administrator-only (AccessError otherwise);
    - _handle_fulfillment_mode_switch_scan: a clean scan completes to Mode 2, a
      blocker (a read that fails, or an external fulfillment forcing a review)
      aborts back to Mode 1.

    fulfillment_operating_mode / _switch_in_progress / _mode_switch_nonce are
    Administrator-grouped fields -> written and read here via sudo().
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.order_binding = cls.env[
            'shopify.connector.order.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id,
            'status': 'active',
        })
        # The acting test user must be a Shopify Connector Administrator to run
        # the mode-switch actions.
        admin_group = cls.env.ref(
            'shopify_connector_core.group_shopify_connector_admin'
        )
        cls.env.user.sudo().write({'group_ids': [(4, admin_group.id)]})
        # A fresh non-admin user for the AccessError paths.
        cls.non_admin = cls.env['res.users'].create({
            'name': 'FUL Non-Admin',
            'login': 'ful-nonadmin-%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    # ------------------------------------------------------------------
    # Job builders
    # ------------------------------------------------------------------

    def _mode2_eval_job(self, state, res_id):
        """An in-flight Mode 2 evaluation job (as inbound routing enqueues it:
        job_source='reconciliation')."""
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': JOB_TYPE_MODE2_EVALUATION,
            'state': state,
            'res_model': 'shopify.connector.fulfillment.inbound.evidence',
            'res_id': res_id,
            'payload_hash': uuid.uuid4().hex,
        })

    def _create_job(self):
        """An in-flight Layer 2 fulfillment_create mutation job (running)."""
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE,
            'state': 'running',
            'res_model': 'stock.picking',
            'res_id': 1,
            'payload_hash': uuid.uuid4().hex,
        })

    def _tracking_job(self):
        """An in-flight Layer 2 fulfillment_tracking_update mutation job."""
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_TRACKING_UPDATE,
            'state': 'running',
            'res_model': 'shopify.connector.fulfillment.binding',
            'res_id': 1,
            'payload_hash': uuid.uuid4().hex,
        })

    def _mutation_job_with_token(self):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': TRIGGER_ORIGIN_PICKING,
            'job_type': JOB_TYPE_CREATE,
            'state': 'queued',
            'res_model': 'stock.picking',
            'res_id': 1,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/1',
            'payload_hash': uuid.uuid4().hex,
        })
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        return job, token

    def _uncertain_attempt(self, job, token):
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'fulfillment_create',
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {},
            'preconditions_snapshot': {'order_gid': 'gid://shopify/Order/1'},
            'business_intent_fingerprint': 'bif',
            'exact_request_fingerprint': 'erf',
            'shopify_idempotency_key': '',
        })
        attempt._record_direct_outcome('uncertain', evidence={})
        return attempt

    def _reconcile_job(self, attempt):
        """An in-flight Layer 2 fulfillment_mutation_reconcile job."""
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_mutation_reconcile',
            'state': 'running',
            'mutation_attempt_id': attempt.id,
            'payload_hash': 'reconcile:%s' % attempt.attempt_token,
            'expected_connection_generation': (
                attempt.expected_connection_generation
            ),
        })

    def _scan_job(self):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': JOB_TYPE_MODE_SWITCH_SCAN,
            'state': 'queued',
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'payload_hash': uuid.uuid4().hex,
        })

    # ------------------------------------------------------------------
    # action_start_mode2_switch
    # ------------------------------------------------------------------

    def test_start_switch_from_mode1_sets_flags_and_enqueues_scan(self):
        # Default operating_mode is Mode 1.
        self.settings.action_start_mode2_switch()
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.sudo().fulfillment_switch_in_progress)
        self.assertTrue(self.settings.sudo().fulfillment_mode_switch_nonce)
        scan = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_MODE_SWITCH_SCAN),
        ])
        self.assertTrue(scan)

    def test_start_switch_idempotent_when_already_mode2(self):
        self.settings.sudo().write({'fulfillment_operating_mode': 'mode2'})
        before = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_MODE_SWITCH_SCAN),
        ])
        result = self.settings.action_start_mode2_switch()
        self.assertTrue(result)
        self.settings.invalidate_recordset()
        # No re-entry into the switching state, no duplicate scan enqueued.
        self.assertFalse(self.settings.sudo().fulfillment_switch_in_progress)
        after = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_MODE_SWITCH_SCAN),
        ])
        self.assertEqual(after, before)

    def test_start_switch_requires_admin(self):
        with self.assertRaises(AccessError):
            self.settings.with_user(self.non_admin).action_start_mode2_switch()

    # ------------------------------------------------------------------
    # action_rollback_to_mode1
    # ------------------------------------------------------------------

    def test_rollback_cancels_mode2_evaluations_but_not_layer2(self):
        self.settings.sudo().write({
            'fulfillment_operating_mode': 'mode2',
            'fulfillment_switch_in_progress': True,
        })
        eval_queued = self._mode2_eval_job('queued', 1)
        eval_retry = self._mode2_eval_job('retry_waiting', 2)
        # In-flight Layer 2 mutation jobs (create / tracking / reconcile).
        create_job, token = self._mutation_job_with_token()
        attempt = self._uncertain_attempt(create_job, token)
        reconcile_job = self._reconcile_job(attempt)
        tracking_job = self._tracking_job()

        self.settings.action_rollback_to_mode1()

        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode1',
        )
        self.assertFalse(self.settings.sudo().fulfillment_switch_in_progress)
        # In-flight Mode 2 evaluations are cancelled back (local only).
        for job in (eval_queued, eval_retry):
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertTrue(job.cancel_reason)
            self.assertTrue(job.finished_at)
        # Layer 2 mutation/reconcile jobs are NOT cancelled by the switch.
        for job in (create_job, reconcile_job, tracking_job):
            job.invalidate_recordset()
            self.assertNotIn(job.state, TERMINAL_JOB_STATES)
            self.assertEqual(job.state, 'running')

    def test_rollback_requires_admin(self):
        self.settings.sudo().write({'fulfillment_operating_mode': 'mode2'})
        with self.assertRaises(AccessError):
            self.settings.with_user(self.non_admin).action_rollback_to_mode1()

    # ------------------------------------------------------------------
    # _handle_fulfillment_mode_switch_scan
    # ------------------------------------------------------------------

    def test_scan_clean_completes_to_mode2(self):
        self.settings.sudo().write({'fulfillment_switch_in_progress': True})
        job = self._scan_job()
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          return_value=[]):
            self.Service._handle_fulfillment_mode_switch_scan(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode2',
        )
        self.assertFalse(self.settings.sudo().fulfillment_switch_in_progress)

    def test_scan_read_error_aborts_to_mode1(self):
        self.settings.sudo().write({
            'fulfillment_operating_mode': 'mode1',
            'fulfillment_switch_in_progress': True,
        })
        job = self._scan_job()
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          side_effect=FulfillmentReadError(
                              'data_shape_schema_mismatch', 'boom')):
            self.Service._handle_fulfillment_mode_switch_scan(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode1',
        )
        self.assertFalse(self.settings.sudo().fulfillment_switch_in_progress)

    def test_scan_external_fulfillment_aborts_to_mode1(self):
        self.settings.sudo().write({'fulfillment_switch_in_progress': True})
        job = self._scan_job()
        node = {
            'id': 'gid://shopify/Fulfillment/EXT',
            'status': 'SUCCESS',
            'displayStatus': 'FULFILLED',
            'trackingInfo': [],
        }
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          return_value=[node]):
            self.Service._handle_fulfillment_mode_switch_scan(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode1',
        )
        self.assertFalse(self.settings.sudo().fulfillment_switch_in_progress)
        # The pre-existing external fulfillment is recorded as a review case
        # (the scan blocker that aborted the switch).
        evidence = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo().search([
            ('store_id', '=', self.store.id),
            ('shopify_fulfillment_gid', '=', 'gid://shopify/Fulfillment/EXT'),
        ], limit=1)
        self.assertEqual(evidence.reconciled_state, 'review')

    # ------------------------------------------------------------------
    # Theme E — watermark-boundary pagination beyond the old 200-row window
    # ------------------------------------------------------------------

    def test_mode_switch_scan_processes_more_than_200_order_bindings(self):
        self.settings.sudo().write({'fulfillment_switch_in_progress': True})
        OrderBinding = self.env['shopify.connector.order.binding']
        for i in range(201):
            sale = self.env['sale.order'].create({
                'partner_id': self.partner.id,
            })
            OrderBinding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Order/MSBULK-%d' % i,
                'sale_order_id': sale.id, 'status': 'active',
            })
        job = self._scan_job()
        call_count = {'n': 0}

        def _counting_read(store, order_gid):
            call_count['n'] += 1
            return []

        with patch.object(type(self.Service), '_read_order_fulfillments',
                          side_effect=_counting_read):
            self.Service._handle_fulfillment_mode_switch_scan(job)
        self.assertGreaterEqual(call_count['n'], 201)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode2',
        )

    def test_mode_switch_scan_incomplete_pass_fails_closed(self):
        self.settings.sudo().write({'fulfillment_switch_in_progress': True})
        OrderBinding = self.env['shopify.connector.order.binding']
        for i in range(3):
            sale = self.env['sale.order'].create({
                'partner_id': self.partner.id,
            })
            OrderBinding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Order/MSCAP-%d' % i,
                'sale_order_id': sale.id, 'status': 'active',
            })
        job = self._scan_job()
        with patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.MAX_SCAN_PAGES', 1,
        ), patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.RECONCILE_BATCH', 2,
        ), patch.object(
            type(self.Service), '_read_order_fulfillments', return_value=[],
        ):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_mode_switch_scan(job)
        self.settings.invalidate_recordset()
        # A failed/incomplete pass never completes the switch either way.
        self.assertTrue(self.settings.sudo().fulfillment_switch_in_progress)

    def test_mode_switch_scan_boundary_excludes_bindings_before_watermark(self):
        # PD-B4: the switch scan boundary derives from the watermark (minus
        # overlap); an order binding touched well BEFORE that boundary and
        # with no unresolved evidence is outside the scan's scope.
        self.settings.sudo().write({
            'fulfillment_switch_in_progress': True,
            'fulfillment_last_reconciliation_at': fields.Datetime.now(),
        })
        boundary = self.Service._mode_switch_scan_boundary(
            self.store, self.settings.sudo(),
        )
        self.assertTrue(boundary)
        # The default lookback floor bounds the boundary to at most 30 days
        # back from now, and no earlier than that even with no watermark.
        floor = fields.Datetime.now() - timedelta(days=30)
        self.assertGreaterEqual(boundary, floor - timedelta(minutes=1))

    def test_mode_switch_scan_boundary_defaults_to_thirty_day_floor(self):
        # No watermark and no unresolved evidence yet (first-ever scan):
        # bounded by the 30-day default lookback, never unbounded.
        boundary = self.Service._mode_switch_scan_boundary(
            self.store, self.settings.sudo(),
        )
        expected_floor = fields.Datetime.now() - timedelta(days=30)
        self.assertAlmostEqual(
            boundary, expected_floor, delta=timedelta(minutes=5),
        )
