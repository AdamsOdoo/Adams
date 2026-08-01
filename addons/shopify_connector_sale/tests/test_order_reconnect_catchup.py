# Part of the Shopify Connector (Store 360 / R-4 slice 1).
#
# Generation-bound order catch-up: admission from the REAL reconnect entry
# point, stale-lineage retirement, pending-lineage recording by the REAL
# run_scan route, quiescence-gated promotion, fencing, the cancelled-import
# resume path, and the long-gap fail-closed refusal.
#
# COUNTERFACTUAL PROPERTY: every capability asserted here is absent at
# a1c5931 — `action_reconnect` enqueued no order work, `run_scan` recorded
# no lineage, the completion stamps did not exist, and a cancelled import
# collided forever — so this file fails against that head for the exact
# reason the batch exists.

from contextlib import contextmanager
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .test_order_import_mapping import OrderImportCase


@tagged('post_install', '-at_install')
class TestOrderReconnectCatchup(OrderImportCase):

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _reconnect(self, store):
        """Drive the REAL `action_reconnect` body (lock, generation compare,
        the domain hooks) with the probe/readiness seams patched to succeed.
        The probe/credential internals themselves are core lifecycle-test
        territory (`test_connection_lifecycle.py`)."""
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

        store.sudo().write({
            'state': 'reconnect_needed', 'credential_present': True,
        })
        with patch.object(Store, '_run_connection_probe', fake_probe), \
                patch.object(Readiness, 'run_for_store', fake_readiness):
            store.action_reconnect()
        store.invalidate_recordset()

    def _scan_jobs(self, store):
        return self.Job.sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_scan'),
        ], order='id')

    def _make_job(self, job_type, state, generation, payload):
        vals = {
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': job_type,
            'state': state,
            'payload_hash': payload,
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
        }
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        if state == 'blocked_manual_review':
            vals['manual_review_subreason'] = 'ambiguous_match'
        return self.Job.sudo().create(vals)

    @contextmanager
    def _result(self, body):
        yield body

    def _patch_scan(self, bodies):
        bodies = iter(bodies)

        def fake_execute(_client, _job, _store, _query, variables=None):
            return self._result(next(bodies))

        client = self.env['shopify.connector.api.client']
        return patch.object(
            type(client), 'execute_business', new=fake_execute,
        )

    def _scan_body(self, nodes):
        return {
            'data': {'orders': {
                'edges': [
                    {'cursor': 'cursor-%d' % index, 'node': node}
                    for index, node in enumerate(nodes)
                ],
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            }},
        }

    def _node(self, suffix, **extra):
        node = {
            'id': 'gid://shopify/Order/%s' % suffix,
            'updatedAt': '2026-07-17T12:00:00Z',
            'createdAt': '2026-07-17T10:00:00Z',
            'edited': False,
            'test': False,
            'cancelledAt': None,
            'displayFinancialStatus': 'PAID',
        }
        node.update(extra)
        return node

    # ------------------------------------------------------------------
    # admission from the real entry point
    # ------------------------------------------------------------------
    def test_reconnect_admits_exactly_one_catchup_and_retires_stale_jobs(self):
        old_generation = self.store.connection_generation
        stale_scan = self._make_job(
            'order_import_scan', 'queued', old_generation, 'stale-scan',
        )
        stale_import = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': '2026-07-17T12:00:00Z',
            'expected_connection_generation': old_generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': 'gid://shopify/Order/Stale',
        })
        self._reconnect(self.store)
        self.assertEqual(self.store.state, 'connected')
        new_generation = self.store.connection_generation
        self.assertGreater(new_generation, old_generation)

        stale_scan.invalidate_recordset()
        stale_import.invalidate_recordset()
        self.assertEqual(stale_scan.state, 'cancelled')
        self.assertEqual(stale_import.state, 'cancelled')
        self.assertIn('later reconnect', stale_scan.cancel_reason)

        live = self._scan_jobs(self.store).filtered(
            lambda job: job.state == 'queued'
        )
        self.assertEqual(len(live), 1,
                         'exactly one current-generation catch-up lineage')
        self.assertEqual(live.job_source, 'reconciliation')
        self.assertEqual(
            live.expected_connection_generation, new_generation,
        )
        # A second admission coalesces on the in-flight scan.
        again = self.store._shopify_connector_admit_order_catchup()
        self.assertEqual(again.id, live.id)

    def test_reconnect_without_sale_domain_admits_nothing(self):
        self.settings.sudo().write({'sale_domain_enabled': False})
        before = self._scan_jobs(self.store)
        self._reconnect(self.store)
        self.assertEqual(self.store.state, 'connected')
        self.assertEqual(self._scan_jobs(self.store), before)
        # And no stamp exists for the new generation: honestly non-current.
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation,
            self.store.connection_generation,
        )

    # ------------------------------------------------------------------
    # pending lineage through the real run_scan route
    # ------------------------------------------------------------------
    def test_run_scan_records_pending_lineage_in_the_same_pass(self):
        job = self._make_job(
            'order_import_scan', 'running',
            self.store.connection_generation, 'lineage-scan',
        )
        before = fields.Datetime.now()
        with self._patch_scan([self._scan_body([self._node('L1')])]):
            self.env['shopify.connector.order.scan'].run_scan(job)
        settings = self.settings
        settings.invalidate_recordset()
        self.assertEqual(
            settings.sale_order_catchup_pending_generation,
            self.store.connection_generation,
        )
        self.assertEqual(
            settings.sale_order_catchup_pending_scan_job_id, job,
        )
        self.assertGreaterEqual(
            settings.sale_order_catchup_pending_upper_bound_at, before,
        )

    def test_failed_scan_records_no_pending_lineage(self):
        job = self._make_job(
            'order_import_scan', 'running',
            self.store.connection_generation, 'failing-scan',
        )
        malformed = {'data': {'orders': {'edges': 'nonsense'}}}
        with self._patch_scan([malformed]):
            with self.assertRaises(JobHandlerError):
                self.env['shopify.connector.order.scan'].run_scan(job)
        self.settings.invalidate_recordset()
        self.assertFalse(self.settings.sale_order_catchup_pending_scan_job_id)

    # ------------------------------------------------------------------
    # promotion: complete traversal + quiescent descendants only
    # ------------------------------------------------------------------
    def _seed_pending(self, generation, upper_bound=None):
        scan = self._make_job(
            'order_import_scan', 'succeeded', generation, 'seed-%s' % generation,
        )
        self.settings.sudo().write({
            'sale_order_catchup_pending_generation': generation,
            'sale_order_catchup_pending_upper_bound_at':
                upper_bound or fields.Datetime.now(),
            'sale_order_catchup_pending_scan_job_id': scan.id,
        })
        return scan

    def test_promotion_waits_for_descendants_then_stamps(self):
        # A non-zero generation, so "not yet stamped" (default 0) and "the
        # current generation" are distinguishable in every assertion.
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        child = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': 'child-1',
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': 'gid://shopify/Order/Child1',
        })
        self.env['shopify.connector.store.settings'] \
            ._shopify_connector_promote_order_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a queued descendant must block the stamp',
        )
        # The LAST descendant's terminal write is what promotes — through
        # the production job.write hook, not a direct call.
        child.sudo().write({
            'state': 'running',
        })
        child.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sale_order_catchup_generation, generation,
        )
        self.assertEqual(
            self.settings.sale_order_catchup_synced_through_at,
            self.settings.sale_order_catchup_pending_upper_bound_at,
        )

    def test_blocking_failure_prevents_the_stamp(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        self._make_job(
            'order_import_sync', 'failed_final', generation, 'perma-fail',
        )
        self.env['shopify.connector.store.settings'] \
            ._shopify_connector_promote_order_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a failed_final import is a coverage hole and must block',
        )

    def test_stale_lineage_never_stamps_a_newer_generation(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        # A second reconnect wins before the descendants settle.
        self.store.sudo().write({
            'connection_generation': generation + 1,
        })
        self.env['shopify.connector.store.settings'] \
            ._shopify_connector_promote_order_catchup(self.store)
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation + 1,
            'the fenced older lineage must not mark the newer generation '
            'current (R-4 §6)',
        )

    # ------------------------------------------------------------------
    # resume of cancelled work (the disconnect-quiesce shape)
    # ------------------------------------------------------------------
    def test_cancelled_import_resumes_exactly_once_with_a_deterministic_key(self):
        node = self._node('Resume1')
        scan_service = self.env['shopify.connector.order.scan']
        self.assertTrue(scan_service._enqueue_order(
            self.store, node, 'scheduled_sync'))
        original = self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', node['id']),
        ])
        self.assertEqual(len(original), 1)
        # The same identity collides while the job is live.
        self.assertFalse(scan_service._enqueue_order(
            self.store, node, 'scheduled_sync'))
        # Cancelled before running — the disconnect quiesce sweep shape.
        original.sudo().write({
            'state': 'cancelled', 'finished_at': fields.Datetime.now(),
        })
        self.assertTrue(
            scan_service._enqueue_order(self.store, node, 'reconciliation'),
            'a cancelled import whose order never landed must resume',
        )
        resumed = self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', node['id']),
            ('id', '!=', original.id),
        ])
        self.assertEqual(len(resumed), 1)
        self.assertEqual(
            resumed.payload_hash,
            '%s#resume:%d' % (node['updatedAt'], original.id),
        )
        # The cancelled predecessor is linked to its one replacement.
        original.invalidate_recordset()
        self.assertEqual(original.superseded_by_job_id, resumed)
        # A second scan pass collides on the SAME resume key: exactly once.
        self.assertFalse(scan_service._enqueue_order(
            self.store, node, 'reconciliation'))
        # Still exactly one replacement after the duplicate attempt.
        self.assertEqual(len(self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', node['id']),
            ('id', '!=', original.id),
        ])), 1)

    # ------------------------------------------------------------------
    # P1-1: a cancelled current-generation descendant is a coverage hole
    # ------------------------------------------------------------------
    def _enable_scheduled_fresh(self):
        """The `complete_current` preconditions OTHER than the stamp, so the
        bridge assertions below turn only on whether the stamp advanced."""
        self.settings.sudo().write({
            'order_scheduled_sync_enabled': True,
            'sale_order_last_import_checkpoint_at': fields.Datetime.now(),
        })
        self.store.invalidate_recordset()

    def _bridge_state(self):
        data = self.env['shopify.connector.ui.dashboard'].with_user(
            self.roles['auditor']
        ).get_store_360_data(self.store.id, '30d')
        return (data.get('bridge') or {}).get('state')

    def _promote(self):
        self.env['shopify.connector.store.settings'] \
            ._shopify_connector_promote_order_catchup(self.store)
        self.settings.invalidate_recordset()

    def test_cancelled_import_blocks_until_linked_replacement_succeeds(self):
        """The reproduced P1-1 and its fix, end to end through the real
        `action_cancel` operator route and the real deterministic resume."""
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._enable_scheduled_fresh()
        self._seed_pending(generation)
        target_gid = 'gid://shopify/Order/CancelCover'
        descendant = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': '2026-07-17T12:00:00Z',
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': target_gid,
        })

        # Cancel the outstanding import through the sanctioned operator route.
        descendant.with_user(self.roles['operator']).action_cancel(
            'operator cancels the outstanding import')
        descendant.invalidate_recordset()
        self.assertEqual(descendant.state, 'cancelled')

        # The cancel must NOT advance the stamp, and the bridge must NOT claim
        # completeness while an order provably never landed.
        self.settings.invalidate_recordset()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a cancelled descendant must not itself promote the stamp',
        )
        self.assertNotEqual(
            self._bridge_state(), 'complete_current',
            'the bridge must not claim complete/current over a cancelled hole',
        )

        # Admit the deterministic replacement through the real resume route.
        node = self._node('CancelCover')
        scan_service = self.env['shopify.connector.order.scan']
        self.assertTrue(
            scan_service._enqueue_order(self.store, node, 'reconciliation'))
        replacement = self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', target_gid),
            ('id', '!=', descendant.id),
        ])
        self.assertEqual(len(replacement), 1)
        self.assertEqual(
            replacement.payload_hash,
            '%s#resume:%d' % (node['updatedAt'], descendant.id),
        )
        # The cancelled predecessor is linked to its one replacement.
        descendant.invalidate_recordset()
        self.assertEqual(descendant.superseded_by_job_id, replacement)

        # A queued replacement still blocks.
        self._promote()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a queued replacement must keep the stamp blocked',
        )
        # A running replacement still blocks.
        replacement.sudo().write({'state': 'running'})
        self._promote()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a running replacement must keep the stamp blocked',
        )

        # Complete the replacement with binding evidence for the target
        # version — the LAST descendant's success is what promotes, via the
        # production job.write hook.
        order2 = self.env['sale.order'].sudo().create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
        })
        self.Binding.sudo().create({
            'store_id': self.store.id,
            'sale_order_id': order2.id,
            'shopify_gid': target_gid,
            'shopify_order_name': '#CancelCover',
            'shopify_updated_at_snapshot':
                scan_service._as_datetime(node['updatedAt']),
        })
        replacement.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sale_order_catchup_generation, generation,
            'promotion happens only after the replacement succeeds',
        )
        self.assertEqual(
            self.settings.sale_order_catchup_synced_through_at,
            self.settings.sale_order_catchup_pending_upper_bound_at,
        )
        self.assertEqual(
            self._bridge_state(), 'complete_current',
            'once every hole is closed the bridge is complete/current again',
        )

    def test_a_cancelled_scan_job_remains_blocking(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        # A cancelled SCAN is a store-wide enumeration hole, never coverable
        # by a single-target replacement.
        self._make_job(
            'order_import_scan', 'cancelled', generation, 'cancelled-scan',
        )
        self._promote()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a cancelled scan must block promotion',
        )

    def test_a_skipped_policy_row_remains_non_blocking(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        self._make_job(
            'order_import_sync', 'skipped', generation, 'skip-policy',
        )
        self._promote()
        self.assertEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a skipped policy decision is not required work and must not block',
        )

    def test_other_store_or_generation_successor_never_covers(self):
        self.store.sudo().write({'connection_generation': 7})
        generation = self.store.connection_generation
        self._seed_pending(generation)
        target_gid = 'gid://shopify/Order/WrongSuccessor'
        # A cancelled current-generation import. (Payloads differ between
        # jobs only to keep the (store, idempotency_key) unique constraint
        # satisfied — the generation, not the payload, is what coverage
        # turns on.)
        self._make_job_with_gid(
            'order_import_sync', 'cancelled', generation,
            'v#cancelled', target_gid,
        )
        # A succeeded import for the SAME target but an OLDER generation must
        # never satisfy coverage (§Order-lineage 9).
        self._make_job_with_gid(
            'order_import_sync', 'succeeded', generation - 1,
            'v#older', target_gid,
        )
        self._promote()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'an older-generation successor cannot cover a cancelled target',
        )
        # A current-generation succeeded import for a DIFFERENT target does
        # not cover it either.
        self._make_job_with_gid(
            'order_import_sync', 'succeeded', generation,
            'v#diff', 'gid://shopify/Order/DifferentTarget',
        )
        self._promote()
        self.assertNotEqual(
            self.settings.sale_order_catchup_generation, generation,
            'a different-target successor cannot cover a cancelled target',
        )
        # The exact same-target, current-generation success finally covers it.
        self._make_job_with_gid(
            'order_import_sync', 'succeeded', generation,
            'v#final', target_gid,
        )
        self._promote()
        self.assertEqual(
            self.settings.sale_order_catchup_generation, generation,
            'the exact same-target current-generation success covers the hole',
        )

    def _make_job_with_gid(self, job_type, state, generation, payload, gid):
        vals = {
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': job_type,
            'state': state,
            'payload_hash': payload,
            'expected_connection_generation': generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': gid,
        }
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        return self.Job.sudo().create(vals)

    def test_skipped_and_failed_final_priors_do_not_auto_resume(self):
        scan_service = self.env['shopify.connector.order.scan']
        for suffix, terminal_state in (
            ('SkipPrior', 'skipped'), ('FailPrior', 'failed_final'),
        ):
            node = self._node(suffix)
            self.assertTrue(scan_service._enqueue_order(
                self.store, node, 'scheduled_sync'))
            prior = self.Job.sudo().search([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'order_import_sync'),
                ('shopify_target_gid', '=', node['id']),
            ])
            # Reach the terminal state through the LEGAL transition path
            # (queued -> running -> terminal), as the dispatcher does.
            prior.sudo().write({'state': 'running'})
            prior.sudo().write({
                'state': terminal_state,
                'finished_at': fields.Datetime.now(),
            })
            self.assertFalse(
                scan_service._enqueue_order(
                    self.store, node, 'reconciliation'),
                '%s must stay a policy/manual decision, never an automatic '
                're-enqueue (DEC-009)' % terminal_state,
            )

    # ------------------------------------------------------------------
    # long gap: fail closed, never silently truncate
    # ------------------------------------------------------------------
    def test_long_gap_without_read_all_orders_fails_closed(self):
        self.settings.sudo().write({
            'sale_order_last_import_checkpoint_at':
                fields.Datetime.subtract(fields.Datetime.now(), days=100),
        })
        job = self._make_job(
            'order_import_scan', 'running',
            self.store.connection_generation, 'gap-scan',
        )
        with self.assertRaises(UserError):
            self.env['shopify.connector.order.scan'].run_scan(job)
        self.settings.invalidate_recordset()
        self.assertFalse(
            self.settings.sale_order_catchup_pending_scan_job_id,
            'a refused long-gap scan must record no lineage',
        )
