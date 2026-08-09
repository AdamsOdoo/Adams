# Part of the Shopify Connector (Store 360 / R-4 slice 1).
#
# The fulfillment reconnect catch-up: genuinely admitted from the REAL
# `action_reconnect` entry point (the handler existed at a1c5931 with zero
# enqueue sites — this file fails there because nothing admits it), the
# job-type-prefixed operation-scope key that lets it coexist with an
# in-flight reconciliation check, the fail-closed pending stamp, the
# quiescence-gated promotion with second-reconnect fencing, and ruling D:
# the dispatch block is the RULE-VISIBLE `stock.picking` population.

from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_fulfillment_reader import FulfillmentReadError
from ..models.shopify_connector_job import (
    JOB_TYPE_RECONCILIATION_CHECK,
    JOB_TYPE_RECONNECT_CATCHUP,
)


@tagged('post_install', '-at_install')
class TestFulfillmentReconnectCatchup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Fulfillment Catchup Store',
            'shop_domain': 'fulfillment-catchup.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'credential_present': True,
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'sale_domain_enabled': False,
            'fulfillment_domain_enabled': True,
        })
        cls.Job = cls.env['shopify.connector.job'].sudo()
        cls.Service = cls.env['shopify.connector.fulfillment.service']

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _reconnect(self):
        Store = type(self.env['shopify.connector.store'])
        Readiness = type(self.env['shopify.connector.readiness.check'])

        def fake_probe(store_self, purpose):
            store_self.sudo().write({
                'last_test_connection_result': 'pass',
                'last_test_connection_at': fields.Datetime.now(),
            })
            return 'completed'

        def fake_readiness(rc_self, target):
            target.sudo().write({
                'last_readiness_result': 'pass',
                'last_readiness_at': fields.Datetime.now(),
            })
            return {'job': None, 'overall_result': 'pass', 'checks': []}

        self.store.sudo().write({
            'state': 'reconnect_needed', 'credential_present': True,
        })
        with patch.object(Store, '_run_connection_probe', fake_probe), \
                patch.object(Readiness, 'run_for_store', fake_readiness):
            self.store.action_reconnect()
        self.store.invalidate_recordset()

    def _catchup_jobs(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_RECONNECT_CATCHUP),
        ], order='id')

    def _catchup_job(self, state='running'):
        import uuid
        return self.Job.create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': JOB_TYPE_RECONNECT_CATCHUP,
            'state': state,
            'payload_hash': 'catchup-%s' % uuid.uuid4().hex[:10],
            'expected_connection_generation':
                self.store.connection_generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
        })

    # ------------------------------------------------------------------
    # admission from the real entry point (was a dead-end at a1c5931)
    # ------------------------------------------------------------------
    def test_reconnect_admits_the_registered_catchup_route(self):
        self.assertFalse(self._catchup_jobs(),
                         'nothing may admit the route before reconnect')
        self._reconnect()
        self.assertEqual(self.store.state, 'connected')
        jobs = self._catchup_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.state, 'queued')
        self.assertEqual(jobs.job_source, 'reconciliation')
        self.assertEqual(
            jobs.expected_connection_generation,
            self.store.connection_generation,
        )
        # A second admission coalesces on the DB-held scope key
        # (idempotent _enqueue_once; flush first so the first lineage's
        # computed key is genuinely in the table, as it is in production
        # where each admission runs in its own transaction).
        self.env.flush_all()
        self.store._shopify_connector_admit_fulfillment_catchup()
        self.assertEqual(len(self._catchup_jobs()), 1)

    def test_reconnect_without_the_domain_admits_nothing(self):
        self.settings.sudo().write({'fulfillment_domain_enabled': False})
        self._reconnect()
        self.assertFalse(self._catchup_jobs())
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation,
            self.store.connection_generation,
        )

    def test_catchup_coexists_with_an_inflight_reconciliation_check(self):
        """The Theme A scope-key gap, closed: the catch-up is job-type-
        prefixed, so it no longer collides with a live reconciliation check
        for the same store."""
        import uuid
        check = self.Service._enqueue_once(
            self.store, 'reconciliation', JOB_TYPE_RECONCILIATION_CHECK,
            'check:%s' % uuid.uuid4().hex[:8],
            'shopify.connector.store', self.store.id,
        )
        self.assertEqual(check.state, 'queued')
        catchup = self.Service._enqueue_once(
            self.store, 'reconciliation', JOB_TYPE_RECONNECT_CATCHUP,
            'catchup:%s' % uuid.uuid4().hex[:8],
            'shopify.connector.store', self.store.id,
        )
        self.assertEqual(catchup.state, 'queued')
        self.assertNotEqual(check.id, catchup.id)
        self.assertNotEqual(
            check.operation_scope_key, catchup.operation_scope_key)

    # ------------------------------------------------------------------
    # fail-closed pending stamp
    # ------------------------------------------------------------------
    def _order_binding(self, suffix):
        order = self.env['sale.order'].sudo().create({
            'partner_id': self.env.ref('base.res_partner_1').id,
            'company_id': self.env.company.id,
        })
        return self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': self.store.id,
            'sale_order_id': order.id,
            'shopify_gid': 'gid://shopify/Order/FC%s' % suffix,
        })

    def test_complete_pass_records_pending_and_partial_pass_does_not(self):
        self._order_binding('A')
        self._order_binding('B')
        Service = type(self.Service)
        job = self._catchup_job()

        with patch.object(
            Service, '_read_order_fulfillments',
            lambda service, store, gid: [],
        ):
            self.Service._handle_fulfillment_reconnect_catchup(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.fulfillment_catchup_pending_generation,
            self.store.connection_generation,
        )
        self.assertEqual(
            self.settings.fulfillment_catchup_pending_job_id, job,
        )

        # The first lineage must be terminal before a second can hold the
        # (store, operation_scope_key) slot — same rule production obeys.
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.env.flush_all()

        # Partial pass: one read fails → the handler raises and the pending
        # stamp does not move to the failing job.
        failing = self._catchup_job()

        def flaky(service, read_job, store, gid):
            if gid.endswith('FCA'):
                raise FulfillmentReadError(
                    'shopify_graphql_throttled', 'boom')
            return []

        with patch.object(Service, '_read_order_fulfillments', flaky):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_reconnect_catchup(failing)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.fulfillment_catchup_pending_job_id, job,
            'a partial traversal must not overwrite the pending claim',
        )

    # ------------------------------------------------------------------
    # promotion + fencing
    # ------------------------------------------------------------------
    def test_promotion_requires_quiescence_and_fences_stale_lineages(self):
        # Non-zero generation so "unstamped" (default 0) and "current" are
        # distinguishable.
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        scan = self._catchup_job(state='succeeded')
        scan.sudo().write({'finished_at': fields.Datetime.now()})
        observed_through = fields.Datetime.now()
        self.settings.sudo().write({
            'fulfillment_catchup_pending_generation': generation,
            'fulfillment_catchup_pending_observed_through_at':
                observed_through,
            'fulfillment_catchup_pending_job_id': scan.id,
        })
        blocker = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_inbound_observation',
            'state': 'queued',
            'payload_hash': 'fc-blocker',
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.order.binding',
            'res_id': 1,
        })
        Settings = self.env['shopify.connector.store.settings']
        Settings._shopify_connector_promote_fulfillment_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation, generation,
            'a queued descendant observation must block the stamp',
        )
        # The descendant's terminal write promotes through the hook.
        blocker.sudo().write({'state': 'running'})
        blocker.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.fulfillment_catchup_generation, generation)
        self.assertEqual(
            self.settings.fulfillment_catchup_observed_through_at,
            observed_through,
        )
        # A newer generation fences the old lineage.
        self.store.sudo().write({'connection_generation': generation + 1})
        Settings._shopify_connector_promote_fulfillment_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation, generation + 1)

    # ------------------------------------------------------------------
    # P1-1: a cancelled current-generation fulfillment descendant is a hole
    # ------------------------------------------------------------------
    def _operator(self):
        return new_test_user(
            self.env, login='fc_operator',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_operator',
        )

    def _auditor(self):
        return new_test_user(
            self.env, login='fc_auditor',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor',
        )

    def _make_order_side_complete(self, generation):
        """Everything the sale-side bridge needs for `complete_current`
        EXCEPT the fulfillment stamp, so the bridge assertion turns only on
        fulfillment coverage."""
        now = fields.Datetime.now()
        self.settings.sudo().write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
            'sale_order_last_import_checkpoint_at': now,
            'sale_order_catchup_generation': generation,
            'sale_order_catchup_synced_through_at': now,
        })
        self.store.invalidate_recordset()

    def _seed_fulfillment_pending(self, generation):
        recording = self._catchup_job(state='succeeded')
        recording.sudo().write({'finished_at': fields.Datetime.now()})
        self.settings.sudo().write({
            'fulfillment_catchup_pending_generation': generation,
            'fulfillment_catchup_pending_observed_through_at':
                fields.Datetime.now(),
            'fulfillment_catchup_pending_job_id': recording.id,
        })
        return recording

    def _bridge_state(self, user):
        data = self.env['shopify.connector.ui.dashboard'].with_user(
            user).get_store_360_data(self.store.id, '30d')
        return (data.get('bridge') or {}).get('state')

    def test_cancelled_fulfillment_descendant_blocks_the_stamp(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._make_order_side_complete(generation)
        self._seed_fulfillment_pending(generation)
        descendant = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_inbound_observation',
            'state': 'queued',
            'payload_hash': 'fc-outstanding',
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.order.binding',
            'res_id': 1,
        })

        # Cancel the outstanding fulfillment work through the operator route.
        descendant.with_user(self._operator()).action_cancel(
            'operator cancels the outstanding fulfillment observation')
        descendant.invalidate_recordset()
        self.assertEqual(descendant.state, 'cancelled')

        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation, generation,
            'a cancelled fulfillment descendant must not advance the stamp',
        )
        self.assertNotEqual(
            self._bridge_state(self._auditor()), 'complete_current',
            'the bridge must not claim complete/current with an open '
            'fulfillment hole',
        )

        # There is NO fulfillment resume route: a later, UNRELATED success at
        # the same generation must not close the cancelled hole.
        other = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_inbound_observation',
            'state': 'queued',
            'payload_hash': 'fc-unrelated',
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.order.binding',
            'res_id': 2,
        })
        other.sudo().write({'state': 'running'})
        other.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation, generation,
            'with no resume route, an unrelated success cannot cover a '
            'cancelled fulfillment descendant',
        )

    def test_a_new_generation_recovers_and_stale_work_cannot_stamp_it(self):
        self.store.sudo().write({'connection_generation': 7})
        old_generation = self.store.connection_generation
        # A cancelled descendant left over from the old generation.
        self.Job.create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_inbound_observation',
            'state': 'cancelled',
            'payload_hash': 'fc-old-cancelled',
            'expected_connection_generation': old_generation,
            'res_model': 'shopify.connector.order.binding',
            'res_id': 1,
            'finished_at': fields.Datetime.now(),
        })
        Settings = self.env['shopify.connector.store.settings']

        # A later reconnect starts a NEW generation; its own complete pass
        # then settles with no current-generation hole.
        self.store.sudo().write({'connection_generation': 8})
        new_generation = self.store.connection_generation
        self._seed_fulfillment_pending(new_generation)
        Settings._shopify_connector_promote_fulfillment_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.fulfillment_catchup_generation, new_generation,
            'the old-generation cancelled lineage is fenced by generation and '
            'must not block the new generation',
        )

        # Stale-generation work can never stamp the new generation: a pending
        # claim recorded for the OLD generation is refused.
        stale_recording = self._catchup_job(state='succeeded')
        stale_recording.sudo().write({'finished_at': fields.Datetime.now()})
        self.settings.sudo().write({
            'fulfillment_catchup_generation': 0,
            'fulfillment_catchup_observed_through_at': False,
            'fulfillment_catchup_pending_generation': old_generation,
            'fulfillment_catchup_pending_observed_through_at':
                fields.Datetime.now(),
            'fulfillment_catchup_pending_job_id': stale_recording.id,
        })
        Settings._shopify_connector_promote_fulfillment_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.fulfillment_catchup_generation, new_generation,
            'a pending claim from an older generation must never stamp the '
            'current one',
        )

    # ------------------------------------------------------------------
    # ruling D: dispatch is the rule-visible picking population
    # ------------------------------------------------------------------
    def test_dispatch_counts_are_governed_by_picking_rules(self):
        binding_a = self._order_binding('D1')
        binding_b = self._order_binding('D2')
        picking_type = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'outgoing'),
             ('company_id', '=', self.env.company.id)], limit=1)
        customer_location = self.env.ref('stock.stock_location_customers')
        pickings = self.env['stock.picking']
        for binding in (binding_a, binding_b):
            pickings |= self.env['stock.picking'].sudo().create({
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': customer_location.id,
                'sale_id': binding.sale_order_id.id,
                'company_id': self.env.company.id,
            })
        visible, hidden = pickings[0], pickings[1]

        restricted_group = self.env['res.groups'].sudo().create(
            {'name': 'S360 Picking Restriction'})
        self.env['ir.rule'].sudo().create({
            'name': 'S360: one visible picking only',
            'model_id': self.env['ir.model'].sudo()._get('stock.picking').id,
            'domain_force': "[('id', '=', %d)]" % visible.id,
            'groups': [(6, 0, [restricted_group.id])],
        })
        user = new_test_user(
            self.env, login='s360_picking_restricted',
            groups='base.group_user,stock.group_stock_user,'
                   'shopify_connector_core.group_shopify_connector_auditor',
        )
        user.sudo().write({'group_ids': [(4, restricted_group.id)]})

        payload = self.env['shopify.connector.ui.dashboard'].with_user(
            user).get_store_360_data(self.store.id, '30d')
        dispatch = payload['dispatch']
        self.assertTrue(dispatch['available'])
        buckets = {b['id']: b for b in dispatch['buckets']}
        self.assertEqual(
            buckets['to_dispatch']['count'], 1,
            'ruling D: only the RULE-VISIBLE picking counts',
        )
        Picking = self.env['stock.picking'].with_user(user)
        domain = [tuple(t) for t in buckets['to_dispatch']['target']['domain']]
        self.assertEqual(Picking.search_count(domain), 1)
        self.assertIn(visible.id, Picking.search(domain).ids)
        self.assertNotIn(hidden.id, Picking.search(domain).ids)
