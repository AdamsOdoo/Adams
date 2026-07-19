import threading
import uuid
from unittest.mock import patch

import psycopg2

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


@tagged('post_install', '-at_install')
class TestMutationConcurrency(TransactionCase):
    """Genuine PostgreSQL independent-connection proof, never simulation."""

    def _durable_fixture(self):
        domain = 'layer2-concurrency-%s.myshopify.com' % uuid.uuid4().hex
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Layer 2 concurrency',
                'shop_domain': domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            job = env['shopify.connector.job'].sudo().create({
                'store_id': store.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'mutation_dispatch_selftest',
                'expected_connection_generation':
                    store.connection_generation,
                'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
            })
            ids = store.id, job.id
            cr.commit()
        self.addCleanup(self._cleanup_fixture, *ids)
        return ids

    def _cleanup_fixture(self, store_id, job_id):
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job_log WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job '
                'WHERE mutation_attempt_id IN ('
                'SELECT id FROM shopify_connector_mutation_attempt '
                'WHERE store_id = %s)',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_mutation_attempt '
                'WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()

    def test_c1_token_ownership_race_has_one_winner(self):
        _store_id, job_id = self._durable_fixture()
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def contender():
            try:
                with db_connect(self.env.cr.dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    barrier.wait(timeout=10)
                    locked = env['shopify.connector.job'].browse(
                        job_id
                    ).try_lock_for_update()
                    results.append(bool(locked))
                    barrier.wait(timeout=10)
                    cr.rollback()
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=contender) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors)
        self.assertEqual(sorted(results), [False, True])

    def test_repeatable_read_requires_fresh_transaction_for_c2_visibility(self):
        store_id, job_id = self._durable_fixture()
        observer = db_connect(self.env.cr.dbname).cursor()
        creator = db_connect(self.env.cr.dbname).cursor()
        try:
            observer.execute(
                'SELECT count(*) FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            self.assertEqual(observer.fetchone()[0], 0)
            creator.execute(
                'INSERT INTO shopify_connector_mutation_attempt '
                '(job_id, attempt_token, mutation_domain, '
                'transport_attempted, observed_outcome, created_at, '
                'create_uid, create_date, write_uid, write_date) '
                "VALUES (%s, %s, %s, TRUE, 'pending', NOW(), %s, NOW(), %s, NOW())",
                (
                    job_id, uuid.uuid4().hex,
                    'mutation_dispatch_selftest', SUPERUSER_ID, SUPERUSER_ID,
                ),
            )
            creator.commit()
            observer.execute(
                'SELECT count(*) FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            self.assertEqual(observer.fetchone()[0], 0)
            observer.commit()
            observer.execute(
                'SELECT count(*) FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            self.assertEqual(observer.fetchone()[0], 1)
        finally:
            observer.rollback()
            creator.rollback()
            observer.close()
            creator.close()
            with db_connect(self.env.cr.dbname).cursor() as cr:
                cr.execute(
                    'DELETE FROM shopify_connector_mutation_attempt '
                    'WHERE job_id = %s',
                    (job_id,),
                )
                cr.commit()
    def _durable_owned_attempt(self, outcome='pending'):
        store_id, job_id = self._durable_fixture()
        token = uuid.uuid4().hex
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            job.sudo().write({
                'state': 'running',
                'current_attempt_token': token,
                'owner_worker_ref': 'concurrency:1',
                'running_since': fields.Datetime.now(),
            })
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].with_context(**{
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': job_id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'expected_connection_generation':
                    job.store_id.connection_generation,
                'expected_store_identity': job.store_id.shop_domain,
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
            if outcome != 'pending':
                attempt._record_direct_outcome(outcome)
            attempt_id = attempt.id
            cr.commit()
        return store_id, job_id, attempt_id, token

    def test_c3_token_mismatch_is_refused_on_fresh_connection(self):
        _store_id, job_id, attempt_id, _token = (
            self._durable_owned_attempt()
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            Dispatch = env['shopify.connector.job.dispatch']
            strategy = Dispatch._get_reconciliation_strategies()[
                'mutation_dispatch_selftest'
            ]
            with self.assertRaises(ValidationError):
                Dispatch._commit_mutation_outcome_c3(
                    job_id,
                    attempt_id,
                    'wrong-owner-token',
                    {'outcome': 'succeeded', 'evidence': {}},
                    strategy,
                )
            cr.rollback()

    def test_c3_local_store_identity_mismatch_blocks_without_resend(self):
        store_id, job_id, attempt_id, token = self._durable_owned_attempt()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'UPDATE shopify_connector_store SET shop_domain = %s '
                'WHERE id = %s',
                ('changed-identity.myshopify.com', store_id),
            )
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            Dispatch = env['shopify.connector.job.dispatch']
            strategy = Dispatch._get_reconciliation_strategies()[
                'mutation_dispatch_selftest'
            ]
            Dispatch._commit_mutation_outcome_c3(
                job_id, attempt_id, token,
                strategy['classify_direct_result']({
                    'outcome': 'succeeded', 'evidence': {},
                }),
                strategy,
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'SELECT state, error_class, current_attempt_token '
                'FROM shopify_connector_job WHERE id = %s',
                (job_id,),
            )
            self.assertEqual(cr.fetchone(), (
                'blocked_manual_review', 'store_identity_mismatch', None,
            ))

    def test_c3_local_generation_mismatch_blocks_without_resend(self):
        store_id, job_id, attempt_id, token = self._durable_owned_attempt()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'UPDATE shopify_connector_store '
                'SET connection_generation = connection_generation + 1 '
                'WHERE id = %s',
                (store_id,),
            )
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            Dispatch = env['shopify.connector.job.dispatch']
            strategy = Dispatch._get_reconciliation_strategies()[
                'mutation_dispatch_selftest'
            ]
            Dispatch._commit_mutation_outcome_c3(
                job_id, attempt_id, token,
                strategy['classify_direct_result']({
                    'outcome': 'succeeded', 'evidence': {},
                }),
                strategy,
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'SELECT state, error_class, current_attempt_token '
                'FROM shopify_connector_job WHERE id = %s',
                (job_id,),
            )
            self.assertEqual(cr.fetchone(), (
                'blocked_manual_review', 'store_identity_mismatch', None,
            ))

    def test_committed_c3_outcomes_clear_active_owner(self):
        for outcome, expected_state in (
            ('succeeded', 'succeeded'), ('uncertain', 'running'),
        ):
            _store_id, job_id, attempt_id, token = (
                self._durable_owned_attempt()
            )
            with db_connect(self.env.cr.dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                Dispatch = env['shopify.connector.job.dispatch']
                strategy = Dispatch._get_reconciliation_strategies()[
                    'mutation_dispatch_selftest'
                ]
                Dispatch._commit_mutation_outcome_c3(
                    job_id, attempt_id, token,
                    strategy['classify_direct_result']({
                        'outcome': outcome, 'evidence': {},
                    }),
                    strategy,
                )
            with db_connect(self.env.cr.dbname).cursor() as cr:
                cr.execute(
                    'SELECT state, current_attempt_token, owner_worker_ref, '
                    'running_since FROM shopify_connector_job WHERE id = %s',
                    (job_id,),
                )
                self.assertEqual(
                    cr.fetchone(), (expected_state, None, None, None),
                )
                if outcome == 'uncertain':
                    cr.execute(
                        'SELECT count(*) FROM shopify_connector_job '
                        'WHERE mutation_attempt_id = %s',
                        (attempt_id,),
                    )
                    self.assertEqual(cr.fetchone()[0], 1)

    def test_concurrent_second_attempt_with_different_tokens_is_rejected(self):
        _store_id, job_id = self._durable_fixture()
        barrier = threading.Barrier(2)
        results = []

        def insert_attempt():
            with db_connect(self.env.cr.dbname).cursor() as cr:
                try:
                    barrier.wait(timeout=10)
                    cr.execute(
                        'INSERT INTO shopify_connector_mutation_attempt '
                        '(job_id, attempt_token, mutation_domain, '
                        'transport_attempted, observed_outcome, created_at, '
                        'create_uid, create_date, write_uid, write_date) '
                        "VALUES (%s, %s, %s, TRUE, 'pending', NOW(), "
                        '%s, NOW(), %s, NOW())',
                        (
                            job_id, uuid.uuid4().hex,
                            'mutation_dispatch_selftest',
                            SUPERUSER_ID, SUPERUSER_ID,
                        ),
                    )
                    cr.commit()
                    results.append('created')
                except Exception:
                    cr.rollback()
                    results.append('rejected')

        threads = [threading.Thread(target=insert_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(sorted(results), ['created', 'rejected'])

    def test_concurrent_stale_sweeps_create_one_reconciliation_job(self):
        store_id, job_id, attempt_id, _token = self._durable_owned_attempt()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'UPDATE shopify_connector_job '
                "SET running_since = NOW() - INTERVAL '1 hour' "
                'WHERE id = %s',
                (job_id,),
            )
            cr.commit()

        barrier = threading.Barrier(2)
        errors = []

        def sweep():
            try:
                with db_connect(self.env.cr.dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    barrier.wait(timeout=10)
                    env['shopify.connector.stale.owner.sweep'].run_sweep()
                    cr.commit()
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=sweep) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors)
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            reconciliations = env['shopify.connector.job'].search([
                ('mutation_attempt_id', '=', attempt_id),
            ])
            self.assertEqual(len(reconciliations), 1)
            self.assertEqual(attempt.observed_outcome, 'uncertain')
            self.assertFalse(attempt.resolved_at)
            self.assertTrue(attempt.remote_evidence_refs['recovery'])
            self.assertEqual(
                attempt.remote_evidence_refs['recovery'][0]['source'],
                'stale_owner_sweep',
            )
            self.assertFalse(original.current_attempt_token)
            self.assertFalse(original.owner_worker_ref)
            self.assertFalse(original.running_since)
            reconciliations.sudo().write({
                'state': 'running',
                'started_at': fields.Datetime.now(),
            })
            env[
                'shopify.connector.job.dispatch'
            ]._handle_mutation_dispatch_selftest_reconcile(reconciliations)
            self.assertEqual(attempt.effective_disposition(), 'applied')
            self.assertEqual(original.state, 'succeeded')
            self.assertEqual(reconciliations.state, 'succeeded')
            cr.commit()

    def test_pre_c2_recovery_that_discovers_c2_marks_uncertain(self):
        _store_id, job_id, attempt_id, token = (
            self._durable_owned_attempt()
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env[
                'shopify.connector.job.dispatch'
            ]._recover_pre_c2_failure(
                job_id, token, RuntimeError('synthetic C2 race'),
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(attempt.observed_outcome, 'uncertain')
            self.assertFalse(attempt.resolved_at)
            self.assertEqual(
                attempt.remote_evidence_refs['recovery'][0]['window'],
                'c2_discovered_during_pre_c2_recovery',
            )
            self.assertFalse(original.current_attempt_token)
            self.assertEqual(env['shopify.connector.job'].search_count([
                ('mutation_attempt_id', '=', attempt_id),
            ]), 1)

    def test_invalid_recovery_state_blocks_without_rewriting_attempt(self):
        _store_id, job_id, attempt_id, token = (
            self._durable_owned_attempt('succeeded')
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env[
                'shopify.connector.job.dispatch'
            ]._recover_layer2_owner(job_id, token)
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(attempt.observed_outcome, 'succeeded')
            self.assertTrue(attempt.resolved_at)
            self.assertEqual(original.state, 'blocked_manual_review')
            self.assertEqual(
                original.manual_review_subreason, 'duplicate_risk',
            )
            self.assertFalse(env['shopify.connector.job'].search_count([
                ('mutation_attempt_id', '=', attempt_id),
            ]))

    def test_no_open_transaction_or_owner_lock_across_net_window(self):
        _store_id, job_id = self._durable_fixture()
        worker = db_connect(self.env.cr.dbname).cursor()
        observer = db_connect(self.env.cr.dbname).cursor()
        try:
            worker.execute('SELECT pg_backend_pid()')
            worker_pid = worker.fetchone()[0]
            worker.execute(
                'UPDATE shopify_connector_job '
                'SET state = %s, current_attempt_token = %s, '
                'owner_worker_ref = %s, running_since = NOW() '
                'WHERE id = %s',
                ('running', uuid.uuid4().hex, 'net-window', job_id),
            )
            worker.commit()
            observer.execute(
                'SELECT state FROM pg_stat_activity WHERE pid = %s',
                (worker_pid,),
            )
            self.assertEqual(observer.fetchone()[0], 'idle')
            observer.execute(
                'SELECT count(*) FROM pg_locks '
                'WHERE pid = %s AND granted '
                "AND locktype IN ('tuple', 'transactionid')",
                (worker_pid,),
            )
            self.assertEqual(observer.fetchone()[0], 0)
        finally:
            worker.rollback()
            observer.rollback()
            worker.close()
            observer.close()

    def test_concurrent_reconciliation_increments_respect_cap(self):
        _store_id, job_id, attempt_id, _token = (
            self._durable_owned_attempt('uncertain')
        )
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def increment():
            barrier.wait(timeout=10)
            for _retry in range(5):
                with db_connect(self.env.cr.dbname).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    try:
                        count = env[
                            'shopify.connector.mutation.attempt'
                        ].browse(
                            attempt_id
                        )._record_inconclusive_reconciliation(False)
                        cr.commit()
                        results.append(count)
                        return
                    except Exception:
                        cr.rollback()
                threading.Event().wait(0.05)
            errors.append('increment retry budget exhausted')

        threads = [threading.Thread(target=increment) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors)
        self.assertEqual(sorted(results), [1, 2])
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            reconciliation = env['shopify.connector.job'].sudo().create({
                'store_id': original.store_id.id,
                'job_source': 'reconciliation',
                'job_type': 'mutation_dispatch_selftest_reconcile',
                'state': 'running',
                'payload_hash': 'cap:%s' % attempt.attempt_token,
                'mutation_attempt_id': attempt.id,
                'expected_connection_generation':
                    attempt.expected_connection_generation,
            })
            Dispatch = env['shopify.connector.job.dispatch']
            strategy = dict(Dispatch._get_reconciliation_strategies()[
                attempt.mutation_domain
            ])
            strategy['reconcile'] = lambda _attempt: {
                'verdict': 'inconclusive',
                'observed_store_identity':
                    attempt.expected_store_identity,
                'action': 'reconcile',
                'error_class': 'shopify_temporary_server_network',
                'manual_review_subreason': False,
                'message': 'Concurrent read remains inconclusive.',
                'evidence': {'read': 'concurrent-cap'},
            }
            with patch.object(
                type(Dispatch), '_get_reconciliation_strategies',
                return_value={attempt.mutation_domain: strategy},
            ):
                Dispatch._handle_mutation_dispatch_selftest_reconcile(
                    reconciliation
                )
            self.assertEqual(
                attempt.inconclusive_reconciliation_count, 3,
            )
            self.assertEqual(original.state, 'blocked_manual_review')
            self.assertEqual(
                original.manual_review_subreason, 'duplicate_risk',
            )
            self.assertEqual(reconciliation.state, 'succeeded')
            self.assertEqual(env['shopify.connector.job.log'].search_count([
                ('job_id', '=', original.id),
                ('to_state', '=', 'blocked_manual_review'),
            ]), 1)
            cr.commit()

    def test_serialization_failure_recovers_to_reconciliation(self):
        _store_id, job_id, attempt_id, token = (
            self._durable_owned_attempt()
        )
        worker = db_connect(self.env.cr.dbname).cursor()
        racer = db_connect(self.env.cr.dbname).cursor()
        try:
            worker.execute(
                'SELECT owner_worker_ref FROM shopify_connector_job '
                'WHERE id = %s',
                (job_id,),
            )
            worker.fetchone()
            racer.execute(
                'UPDATE shopify_connector_job SET owner_worker_ref = %s '
                'WHERE id = %s',
                ('racer', job_id),
            )
            racer.commit()
            with self.assertRaises(psycopg2.errors.SerializationFailure):
                worker.execute(
                    'UPDATE shopify_connector_job SET running_since = NOW() '
                    'WHERE id = %s',
                    (job_id,),
                )
            worker.rollback()
            env = api.Environment(worker, SUPERUSER_ID, {})
            env['shopify.connector.job.dispatch']._recover_layer2_owner(
                job_id, token,
            )
            worker.commit()
        finally:
            worker.rollback()
            racer.rollback()
            worker.close()
            racer.close()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(attempt.observed_outcome, 'uncertain')
            self.assertTrue(attempt.remote_evidence_refs['recovery'])
            self.assertEqual(
                attempt.remote_evidence_refs['recovery'][0]['source'],
                'dispatcher_recovery',
            )
            self.assertFalse(original.current_attempt_token)
            self.assertEqual(env['shopify.connector.job'].search_count([
                ('mutation_attempt_id', '=', attempt_id),
            ]), 1)

    def test_second_worker_cannot_claim_durably_owned_job(self):
        _store_id, job_id, _attempt_id, _token = (
            self._durable_owned_attempt()
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            claimed = env['shopify.connector.job']._claim_for_dispatch(20)
            self.assertNotIn(job_id, claimed.ids)
            cr.rollback()
