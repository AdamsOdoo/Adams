import multiprocessing
import os
import time
import uuid
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import Mock, patch

from odoo import SUPERUSER_ID, api, fields
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, new_test_user, tagged

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


def _layer2_death_worker(dbname, job_id, phase, ready):
    """Real child process: commit boundaries survive os._exit/terminate."""
    with db_connect(dbname).cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Dispatch = env['shopify.connector.job.dispatch']
        job = env['shopify.connector.job'].browse(job_id)
        strategy = Dispatch._get_reconciliation_strategies()[
            'mutation_dispatch_selftest'
        ]
        local = strategy['prepare_local'](job)
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
        owner = {'job_id': job.id, 'attempt_token': token}
        if phase == 'during_precondition':
            ready.set()
            time.sleep(300)
        request = strategy['prepare_preconditions'](local, owner)
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


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
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
        cls.store._p15_set_activation('active')
        cls.mode_admin = new_test_user(
            cls.env,
            login='layer2_recovery_mode_admin_%s' % uuid.uuid4().hex,
            groups=(
                'base.group_user,'
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            company_id=cls.store.company_id.id,
            company_ids=[(6, 0, [cls.store.company_id.id])],
        )
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Sweep = cls.env['shopify.connector.stale.owner.sweep']

    def _running(self, with_attempt):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'dead:1',
            'running_since': fields.Datetime.now() - timedelta(hours=1),
        })
        attempt = False
        if with_attempt:
            attempt = self.Attempt.with_context(**{
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'expected_connection_generation':
                    self.store.connection_generation,
                'expected_store_identity': self.store.shop_domain,
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
        return job, attempt

    def _v2_running(self, running_since, store=None):
        store = self.store if store is None else store
        fixture_env = store.with_company(store.company_id).env
        if store.activation_state != 'active':
            store._p15_set_activation('active')
        settings = fixture_env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if not settings:
            settings = fixture_env[
                'shopify.connector.store.settings'
            ].sudo()._settings_service_create(
                '_canonical_settings', {'store_id': store.id},
            )
        if settings.v2_runtime_mode != 'all':
            mode_admin = self.mode_admin.sudo()
            if store.company_id not in mode_admin.company_ids:
                mode_admin.write({
                    'company_ids': [(4, store.company_id.id)],
                })
            settings.with_user(mode_admin).with_company(
                store.company_id,
            )._set_v2_modes_service(
                {'v2_runtime_mode': 'all'},
                reason='Layer 2 recovery native regression',
                expected_configuration_generation=(
                    settings.configuration_generation
                ),
            )
        run = fixture_env['shopify.connector.run']._create_service({
            'store_id': store.id,
            'workflow': 'core',
            'operation': 'mutation_dispatch_selftest',
            'trigger': 'system',
            'scope_summary': 'Layer 2 stale-owner regression',
            'configuration_snapshot': {},
        })
        run._admit_service()
        token = uuid.uuid4().hex
        job = fixture_env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                store.connection_generation,
            'expected_configuration_generation':
                settings.configuration_generation,
            'run_id': run.id,
            'lane': 'interactive',
            'lane_priority': 100,
            'available_at': running_since,
            'sequence': 0,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'stale-v2-regression',
            'running_since': running_since,
        })
        Dispatch = fixture_env['shopify.connector.job.dispatch']
        with patch.object(
            type(Dispatch), '_get_v2_mutation_job_types',
            return_value=frozenset(('mutation_dispatch_selftest',)),
        ):
            attempt = fixture_env['shopify.connector.mutation.attempt'].with_context(**{
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'expected_connection_generation':
                    store.connection_generation,
                'expected_store_identity': store.shop_domain,
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
        return job, attempt

    def test_admin_stale_sweep_excludes_older_foreign_c1_and_c2_before_limit(self):
        foreign_company = self.env['res.company'].sudo().create({
            'name': 'Stale sweep foreign %s' % uuid.uuid4().hex,
        })
        foreign_store = self.store.sudo().copy({
            'company_id': foreign_company.id,
            'shop_domain': 'stale-foreign-%s.myshopify.com' % uuid.uuid4().hex,
        })
        now = fields.Datetime.now()
        local, local_attempt = self._v2_running(now - timedelta(hours=1))
        foreign, foreign_attempt = self._v2_running(
            now - timedelta(hours=3), store=foreign_store,
        )
        foreign_c1 = foreign.copy({
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': uuid.uuid4().hex,
        })
        admin = new_test_user(
            self.env, login='stale_scope_%s' % uuid.uuid4().hex,
            groups='base.group_user,shopify_connector_core.group_shopify_connector_admin',
            company_id=self.store.company_id.id,
            company_ids=[(6, 0, [self.store.company_id.id])],
        )
        scoped = self.Sweep.with_user(admin).with_context(
            allowed_company_ids=[self.store.company_id.id],
        )
        Dispatch = self.env['shopify.connector.job.dispatch']
        with patch.object(
            type(Dispatch), '_get_v2_mutation_job_types',
            return_value=frozenset(('mutation_dispatch_selftest',)),
        ), patch.object(
            type(scoped), '_positive_int_parameter',
            side_effect=lambda name, default: 1 if name.endswith('batch_size') else 30,
        ):
            self.assertEqual(scoped.run_sweep(), 1)
        foreign.invalidate_recordset()
        foreign_c1.invalidate_recordset()
        self.assertEqual(foreign.state, 'running')
        self.assertEqual(foreign_c1.state, 'running')
        self.assertFalse(self.Job.sudo().search([
            ('mutation_attempt_id', '=', foreign_attempt.id),
        ]))
        self.assertTrue(self.Job.sudo().search([
            ('mutation_attempt_id', '=', local_attempt.id),
        ]))

    def test_c2_same_company_run_drift_projects_authoritative_attempt_run(self):
        now = fields.Datetime.now()
        job, attempt = self._v2_running(now - timedelta(hours=1))
        attempt_run = attempt.run_id
        other_store = self.store.sudo().copy({
            'shop_domain': 'stale-same-company-%s.myshopify.com' % uuid.uuid4().hex,
        })
        _other_job, other_attempt = self._v2_running(now, store=other_store)
        other_run = other_attempt.run_id
        self.env.cr.execute(
            'UPDATE shopify_connector_job SET run_id = %s WHERE id = %s',
            [other_run.id, job.id],
        )
        job.invalidate_recordset(['run_id'])
        self.assertEqual(job.run_id, other_run)

        Dispatch = self.env['shopify.connector.job.dispatch']
        projected_runs = []

        def record_projection(_dispatch, run):
            projected_runs.append(run)

        with patch.object(
            type(Dispatch), '_get_v2_mutation_job_types',
            return_value=frozenset(('mutation_dispatch_selftest',)),
        ), patch.object(
            type(Dispatch), '_v2_project_run', new=record_projection,
            create=True,
        ):
            self.assertEqual(self.Sweep._sweep_v2_mutation_owners(), 1)

        reconciliation = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliation), 1)
        self.assertEqual(reconciliation.run_id, attempt_run)
        self.assertEqual(projected_runs, [attempt_run])

    def test_c1_without_c2_is_safely_requeued(self):
        job, _attempt = self._running(False)
        self.Sweep.run_sweep()
        self.assertEqual(job.state, 'retry_waiting')
        self.assertFalse(job.current_attempt_token)
        self.assertFalse(self.Attempt.search_count([
            ('job_id', '=', job.id),
        ]))
        self.assertFalse(self.Job.search_count([
            ('mutation_attempt_id.job_id', '=', job.id),
        ]))

    def test_committed_c2_routes_to_one_reconciliation_job(self):
        job, attempt = self._running(True)
        self.Sweep.run_sweep()
        self.Sweep.run_sweep()
        reconciliations = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliations), 1)
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        self.assertFalse(attempt.resolved_at)
        self.assertTrue(attempt.remote_evidence_refs['recovery'])
        self.assertEqual(job.state, 'running')
        self.assertFalse(job.current_attempt_token)
        self.assertFalse(job.owner_worker_ref)
        self.assertFalse(job.running_since)
        transport = Mock(side_effect=AssertionError(
            'recovery must not replay mutation transport'
        ))
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        strategy['transport'] = transport
        reconciliations.sudo().write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })
        with patch.object(
            type(Dispatch), '_get_reconciliation_strategies',
            return_value={attempt.mutation_domain: strategy},
        ):
            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                reconciliations
            )
        transport.assert_not_called()
        self.assertEqual(attempt.effective_disposition(), 'applied')
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(reconciliations.state, 'succeeded')

    def test_committed_c2_token_drift_still_reconciles_once(self):
        job, attempt = self._running(True)
        job.sudo().write({'current_attempt_token': uuid.uuid4().hex})

        self.Sweep.run_sweep()
        self.Sweep.run_sweep()

        reconciliations = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliations), 1)
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        self.assertNotEqual(
            attempt.attempt_token, job.current_attempt_token,
        )
        self.assertFalse(job.current_attempt_token)
        self.assertFalse(job.owner_worker_ref)
        self.assertNotEqual(job.state, 'retry_waiting')

    def test_v2_c2_selection_limits_after_oldest_job_ordering(self):
        now = fields.Datetime.now()
        newer_job, newer_attempt = self._v2_running(
            now - timedelta(hours=1),
        )
        older_job, older_attempt = self._v2_running(
            now - timedelta(hours=2),
        )
        self.assertLess(newer_attempt.id, older_attempt.id)

        selected = self.Sweep._stale_v2_attempt_jobs(
            job_types=frozenset(('mutation_dispatch_selftest',)),
            cutoff=now - timedelta(minutes=30),
            limit=1,
        )

        self.assertEqual(selected, older_job)
        self.assertNotEqual(selected, newer_job)

    def test_v2_c2_job_drift_is_discovered_and_only_reconciled(self):
        job, attempt = self._v2_running(
            fields.Datetime.now() - timedelta(hours=1),
        )
        run = attempt.run_id
        job.sudo().write({
            'run_id': False,
            'job_type': 'core_manual_maintenance',
            'current_attempt_token': False,
        })
        Dispatch = self.env['shopify.connector.job.dispatch']
        with patch.object(
            type(Dispatch), '_get_v2_mutation_job_types',
            return_value=frozenset(('mutation_dispatch_selftest',)),
        ), patch.object(
            type(Dispatch), '_transport_mutation_dispatch_selftest',
            side_effect=AssertionError('stale recovery replayed transport'),
        ) as transport:
            processed = self.Sweep._sweep_v2_mutation_owners()

        self.assertEqual(processed, 1)
        attempt.invalidate_recordset()
        job.invalidate_recordset()
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        self.assertFalse(job.current_attempt_token)
        reconciliation = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliation), 1)
        self.assertEqual(reconciliation.run_id, run)
        self.assertEqual(reconciliation.parent_job_id, job)
        self.assertEqual(reconciliation.lane, 'safety_verification')
        transport.assert_not_called()

    def test_legacy_lock_contention_keeps_v2_processed_count(self):
        candidates = Mock()
        candidates.try_lock_for_update.return_value = self.Job.browse()
        with patch.object(
            type(self.Sweep), '_sweep_v2_mutation_owners',
            return_value=3,
        ), patch.object(
            type(self.Job), 'search', return_value=candidates,
        ):
            self.assertEqual(self.Sweep.run_sweep(), 3)

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
            'after_c1', 'during_precondition', 'after_c2', 'during_net',
            'after_net', 'during_c3',
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
                            phase.replace('_', '-'), uuid.uuid4().hex[:16],
                        ),
                        'api_version': '2026-07',
                        'state': 'connected',
                    })
                    store._p15_set_activation('active')
                    job = env['shopify.connector.job'].sudo().create({
                        'store_id': store.id,
                        'job_source': 'setup_readiness_check',
                        'job_type': 'mutation_dispatch_selftest',
                        'expected_connection_generation':
                            store.connection_generation,
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
                    if phase in ('after_c1', 'during_precondition'):
                        self.assertEqual(recovered.state, 'retry_waiting')
                        self.assertFalse(env[
                            'shopify.connector.mutation.attempt'
                        ].search_count([('job_id', '=', job.id)]))
                        self.assertFalse(env[
                            'shopify.connector.job'
                        ].search_count([
                            ('mutation_attempt_id.job_id', '=', job.id),
                        ]))
                        self.assertFalse(recovered.current_attempt_token)
                        self.assertFalse(recovered.owner_worker_ref)
                    else:
                        attempt = env[
                            'shopify.connector.mutation.attempt'
                        ].search([('job_id', '=', job.id)])
                        self.assertEqual(len(attempt), 1)
                        self.assertEqual(
                            attempt.observed_outcome, 'uncertain',
                        )
                        self.assertFalse(attempt.resolved_at)
                        self.assertTrue(
                            attempt.remote_evidence_refs['recovery']
                        )
                        self.assertEqual(recovered.state, 'running')
                        self.assertFalse(recovered.current_attempt_token)
                        self.assertFalse(recovered.owner_worker_ref)
                        self.assertFalse(recovered.running_since)
                        reconciliations = env[
                            'shopify.connector.job'
                        ].search([
                            ('mutation_attempt_id', '=', attempt.id),
                        ])
                        self.assertEqual(len(reconciliations), 1)
                        transport = Mock(side_effect=AssertionError(
                            'recovery must not replay mutation transport'
                        ))
                        Dispatch = env[
                            'shopify.connector.job.dispatch'
                        ]
                        strategy = dict(
                            Dispatch._get_reconciliation_strategies()[
                                attempt.mutation_domain
                            ]
                        )
                        strategy['transport'] = transport
                        reconciliations.sudo().write({
                            'state': 'running',
                            'started_at': fields.Datetime.now(),
                        })
                        with patch.object(
                            type(Dispatch),
                            '_get_reconciliation_strategies',
                            return_value={
                                attempt.mutation_domain: strategy,
                            },
                        ):
                            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                                reconciliations
                            )
                        transport.assert_not_called()
                        self.assertEqual(
                            attempt.effective_disposition(), 'applied',
                        )
                        self.assertEqual(recovered.state, 'succeeded')
                        self.assertEqual(
                            reconciliations.state, 'succeeded',
                        )
                    cr.commit()
        finally:
            with db_connect(dbname).cursor() as cr:
                job_ids = [job_id for _store_id, job_id in durable]
                store_ids = [store_id for store_id, _job_id in durable]
                if job_ids:
                    cr.execute(
                        'DELETE FROM shopify_connector_job_log '
                        'WHERE store_id = ANY(%s)',
                        (store_ids,),
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
                        'DELETE FROM shopify_connector_job '
                        'WHERE store_id = ANY(%s)',
                        (store_ids,),
                    )
                    cr.execute(
                        'DELETE FROM shopify_connector_store WHERE id = ANY(%s)',
                        (store_ids,),
                    )
                    cr.commit()
