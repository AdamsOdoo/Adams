import multiprocessing
import os
import time
import uuid
from datetime import timedelta
from unittest import skipUnless

from odoo import SUPERUSER_ID, api, fields
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase


def _layer2_death_worker(dbname, job_id, phase, ready):
    """Real child process: commit boundaries survive os._exit/terminate."""
    with db_connect(dbname).cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Dispatch = env['shopify.connector.job.dispatch']
        job = env['shopify.connector.job'].browse(job_id)
        strategy = Dispatch._get_reconciliation_strategies()[
            'mutation_dispatch_selftest'
        ]
        request = strategy['prepare'](job)
        token = uuid.uuid4().hex
        job.sudo().write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'current_attempt_token': token,
            'owner_worker_ref': 'death-harness:%s' % os.getpid(),
            'running_since': fields.Datetime.now() - timedelta(hours=1),
        })
        cr.commit()
        if phase == 'after_c1':
            ready.set()
            os._exit(71)
        attempt_id = Dispatch._commit_attempt_intent_c2(
            job_id, token, request,
        )
        if phase == 'after_c2':
            ready.set()
            os._exit(72)
        if phase == 'during_net':
            ready.set()
            time.sleep(300)
        result = strategy['transport'](
            request,
            {
                'job_id': job_id,
                'attempt_id': attempt_id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
            },
        )
        if phase == 'after_net':
            ready.set()
            os._exit(73)
        if phase == 'during_c3':
            locked = env['shopify.connector.job'].browse(
                job_id
            ).try_lock_for_update()
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id).try_lock_for_update()
            if locked and attempt:
                attempt._record_direct_outcome(
                    result['outcome'], evidence=result['evidence'],
                )
            ready.set()
            time.sleep(300)
        os._exit(74)


class TestMutationRecovery(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 recovery test',
            'shop_domain': 'layer2-recovery-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Sweep = cls.env['shopify.connector.stale.owner.sweep']

    def _running(self, with_attempt):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'dead:1',
            'running_since': fields.Datetime.now() - timedelta(hours=1),
        })
        attempt = False
        if with_attempt:
            attempt = self.Attempt.with_context(
                shopify_layer2_c2_side_cursor=True,
            )._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
        return job, attempt

    def test_c1_without_c2_is_safely_requeued(self):
        job, _attempt = self._running(False)
        self.Sweep.run_sweep()
        self.assertEqual(job.state, 'retry_waiting')
        self.assertFalse(job.current_attempt_token)

    def test_committed_c2_routes_to_one_reconciliation_job(self):
        job, attempt = self._running(True)
        self.Sweep.run_sweep()
        self.Sweep.run_sweep()
        reconciliations = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliations), 1)
        self.assertEqual(job.state, 'running')

    def test_disconnect_preserves_credentials_for_unresolved_attempt(self):
        self.env['shopify.connector.store.credential'].action_set_token(
            self.store, 'shpat_DUMMYDUMMYDUMMY0000000000000000'
        )
        self._running(True)
        self.store.action_disconnect()
        self.store.write({
            'disconnect_requested_at':
                fields.Datetime.now() - timedelta(hours=1),
        })
        self.store._process_disconnect_quiesce()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertTrue(self.store.credential_present)
        self.assertIn('Credentials were preserved', self.store.disconnect_status_reason)

    def test_tunable_defaults_reject_invalid_values(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(
            'shopify_connector.layer2_stale_owner_timeout_minutes', '-1'
        )
        params.set_param(
            'shopify_connector.layer2_stale_owner_batch_size', 'invalid'
        )
        self.assertEqual(
            self.Sweep._positive_int_parameter(
                'shopify_connector.layer2_stale_owner_timeout_minutes', 30
            ),
            30,
        )
        self.assertEqual(
            self.Sweep._positive_int_parameter(
                'shopify_connector.layer2_stale_owner_batch_size', 20
            ),
            20,
        )
        params.set_param(
            'shopify_connector.layer2_stale_owner_batch_size', '7'
        )
        self.assertEqual(
            self.Sweep._positive_int_parameter(
                'shopify_connector.layer2_stale_owner_batch_size', 20
            ),
            7,
        )

    @skipUnless(
        os.getenv('SHOPIFY_LAYER2_RUN_PROCESS_DEATH') == '1',
        'real process-death harness is opt-in outside Odoo.sh',
    )
    def test_real_process_death_harness(self):
        phases = (
            'after_c1', 'after_c2', 'during_net', 'after_net', 'during_c3',
        )
        dbname = self.env.cr.dbname
        durable = []
        try:
            for phase in phases:
                with db_connect(dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    store = env['shopify.connector.store'].create({
                        'name': 'Layer 2 death %s' % phase,
                        'shop_domain': 'layer2-death-%s-%s.myshopify.com' % (
                            phase, uuid.uuid4().hex,
                        ),
                        'api_version': '2026-07',
                    })
                    job = env['shopify.connector.job'].sudo().create({
                        'store_id': store.id,
                        'job_source': 'setup_readiness_check',
                        'job_type': 'mutation_dispatch_selftest',
                        'state': 'queued',
                        'payload_hash': uuid.uuid4().hex,
                    })
                    durable.append((store.id, job.id))
                    cr.commit()
                ready = multiprocessing.Event()
                process = multiprocessing.get_context('fork').Process(
                    target=_layer2_death_worker,
                    args=(dbname, job.id, phase, ready),
                )
                process.start()
                self.assertTrue(ready.wait(30), phase)
                if process.is_alive():
                    process.terminate()
                process.join(30)
                self.assertFalse(process.is_alive(), phase)
                with db_connect(dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    env['shopify.connector.stale.owner.sweep'].run_sweep()
                    recovered = env['shopify.connector.job'].browse(job.id)
                    if phase == 'after_c1':
                        self.assertEqual(recovered.state, 'retry_waiting')
                    else:
                        self.assertEqual(recovered.state, 'running')
                        self.assertTrue(env['shopify.connector.job'].search([
                            ('mutation_attempt_id', '!=', False),
                            ('store_id', '=', store.id),
                        ], limit=1))
                    cr.commit()
        finally:
            with db_connect(dbname).cursor() as cr:
                job_ids = [job_id for _store_id, job_id in durable]
                store_ids = [store_id for store_id, _job_id in durable]
                if job_ids:
                    cr.execute(
                        'DELETE FROM shopify_connector_job_log '
                        'WHERE job_id = ANY(%s)',
                        (job_ids,),
                    )
                    cr.execute(
                        'DELETE FROM shopify_connector_job '
                        'WHERE mutation_attempt_id IN ('
                        'SELECT id FROM shopify_connector_mutation_attempt '
                        'WHERE job_id = ANY(%s))',
                        (job_ids,),
                    )
                    cr.execute(
                        'DELETE FROM shopify_connector_mutation_attempt '
                        'WHERE job_id = ANY(%s)',
                        (job_ids,),
                    )
                    cr.execute(
                        'DELETE FROM shopify_connector_job WHERE id = ANY(%s)',
                        (job_ids,),
                    )
                    cr.execute(
                        'DELETE FROM shopify_connector_store WHERE id = ANY(%s)',
                        (store_ids,),
                    )
                    cr.commit()
