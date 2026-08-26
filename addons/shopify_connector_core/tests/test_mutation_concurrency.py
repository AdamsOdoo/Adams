import ast
import inspect
import queue
import threading
import textwrap
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg2
import psycopg2.errorcodes

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError, ValidationError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestMutationConcurrency(TransactionCase):
    """Genuine PostgreSQL independent-connection proof, never simulation."""

    def _run_raw_sql_workers(self, worker_functions, timeout=20):
        """Run the SQL-only structural uniqueness proof."""
        channels = {
            name: queue.Queue(maxsize=1) for name, _worker in worker_functions
        }

        def invoke(name, worker):
            try:
                result = dict(worker())
                result.setdefault('outcome', 'completed')
                result.setdefault('exception_class', False)
                result.setdefault('sqlstate', False)
                result.setdefault('retry_reasons', ())
            except BaseException as exc:
                result = {
                    'outcome': 'unexpected_exception',
                    'exception_class': type(exc).__name__,
                    'sqlstate': getattr(exc, 'pgcode', False),
                    'retry_reasons': (),
                    'exception': repr(exc),
                }
            result['worker'] = name
            channels[name].put_nowait(result)

        threads = [
            threading.Thread(
                name='layer2-sql-%s' % name,
                target=invoke,
                args=(name, worker),
            )
            for name, worker in worker_functions
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=timeout)
        alive = [thread.name for thread in threads if thread.is_alive()]
        self.assertFalse(
            alive,
            'SQL worker threads exceeded %ss: %s' % (timeout, alive),
        )

        records = []
        for name, _worker in worker_functions:
            self.assertEqual(
                channels[name].qsize(), 1,
                'worker %s must report exactly once' % name,
            )
            records.append(channels[name].get_nowait())
        unexpected = [
            record for record in records
            if record['outcome'] == 'unexpected_exception'
        ]
        self.assertFalse(unexpected, 'worker failure(s): %r' % unexpected)
        return records

    def test_external_concurrency_harness_contract(self):
        harness_path = Path(__file__).with_name(
            'runtime_layer2_concurrency_harness.py'
        )
        source = harness_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(harness_path))
        methods = {
            node.name for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue({
            'run_c1_ownership_race',
            'run_concurrent_inconclusive_increment',
            'run_concurrent_stale_sweep',
        } <= methods)
        self.assertIn("get_context('spawn')", source)
        self.assertNotIn('fork', source.lower())
        child = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == '_child_entry'
        )
        child_source = ast.unparse(child)
        new_environment = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == '_new_environment'
        )
        runtime = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == '_runtime'
        )
        self.assertIn('_new_environment(settings)', child_source)
        self.assertIn('_runtime(settings)', ast.unparse(new_environment))
        self.assertIn("runtime['api'].Environment", ast.unparse(
            new_environment
        ))
        self.assertIn('Registry(settings[\'database\'])', ast.unparse(runtime))
        package_init = Path(__file__).with_name('__init__.py').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('runtime_layer2_concurrency_harness', package_init)

    def test_standard_worker_threads_are_sql_only(self):
        source = textwrap.dedent(inspect.getsource(type(self)))
        tree = ast.parse(source)
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        violations = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {'start', 'join'}
            ):
                continue
            owner = parents.get(node)
            while owner and not isinstance(owner, ast.FunctionDef):
                owner = parents.get(owner)
            if not owner or owner.name != '_run_raw_sql_workers':
                violations.append((node.func.attr, node.lineno))
        self.assertFalse(violations, violations)
        runner = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_run_raw_sql_workers'
        )
        uniqueness = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == (
                'test_concurrent_second_attempt_with_different_tokens_'
                'is_rejected'
            )
        )
        worker = next(
            node for node in uniqueness.body
            if isinstance(node, ast.FunctionDef)
            and node.name == 'insert_attempt'
        )
        self.assertNotIn('api.Environment', ast.unparse(runner))
        self.assertNotIn('api.Environment', ast.unparse(worker))

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
                'SELECT id FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            attempt_ids = [row[0] for row in cr.fetchall()]
            child_job_ids = []
            if attempt_ids:
                cr.execute(
                    'SELECT id FROM shopify_connector_job '
                    'WHERE mutation_attempt_id = ANY(%s)',
                    (attempt_ids,),
                )
                child_job_ids = [row[0] for row in cr.fetchall()]
            fixture_job_ids = sorted(set([job_id] + child_job_ids))
            cr.execute(
                'DELETE FROM shopify_connector_job_log '
                'WHERE store_id = %s OR job_id = ANY(%s)',
                (store_id, fixture_job_ids),
            )
            if child_job_ids:
                cr.execute(
                    'DELETE FROM shopify_connector_job '
                    'WHERE id = ANY(%s)',
                    (child_job_ids,),
                )
            cr.execute(
                'DELETE FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job '
                'WHERE id = %s OR store_id = %s',
                (job_id, store_id),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            checks = {
                'stores': (
                    'SELECT count(*) FROM shopify_connector_store '
                    'WHERE id = %s', (store_id,),
                ),
                'original_jobs': (
                    'SELECT count(*) FROM shopify_connector_job '
                    'WHERE id = %s', (job_id,),
                ),
                'attempts': (
                    'SELECT count(*) '
                    'FROM shopify_connector_mutation_attempt '
                    'WHERE job_id = %s OR id = ANY(%s)',
                    (job_id, attempt_ids),
                ),
                'logs': (
                    'SELECT count(*) FROM shopify_connector_job_log '
                    'WHERE store_id = %s OR job_id = ANY(%s)',
                    (store_id, fixture_job_ids),
                ),
            }
            if child_job_ids:
                checks['child_jobs'] = (
                    'SELECT count(*) FROM shopify_connector_job '
                    'WHERE id = ANY(%s)', (child_job_ids,),
                )
            residue = {}
            for label, (query, params) in checks.items():
                cr.execute(query, params)
                residue[label] = cr.fetchone()[0]
            self.assertFalse(
                any(residue.values()),
                'fixture cleanup failed store_id=%s job_id=%s '
                'attempt_ids=%s child_job_ids=%s counts=%s' % (
                    store_id, job_id, attempt_ids, child_job_ids, residue,
                ),
            )

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

    @mute_logger('odoo.sql_db')
    def test_concurrent_second_attempt_with_different_tokens_is_rejected(self):
        _store_id, job_id = self._durable_fixture()
        start = threading.Barrier(2)

        def insert_attempt():
            cr = db_connect(self.env.cr.dbname).cursor()
            try:
                start.wait(timeout=10)
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
                return {'outcome': 'created'}
            except psycopg2.IntegrityError as exc:
                cr.rollback()
                return {
                    'outcome': 'unique_violation',
                    'exception_class': type(exc).__name__,
                    'sqlstate': exc.pgcode,
                }
            finally:
                cr.rollback()
                cr.close()

        records = self._run_raw_sql_workers([
            ('unique-insert-1', insert_attempt),
            ('unique-insert-2', insert_attempt),
        ])
        created = [row for row in records if row['outcome'] == 'created']
        rejected = [
            row for row in records if row['outcome'] == 'unique_violation'
        ]
        self.assertEqual(len(created), 1, records)
        self.assertEqual(len(rejected), 1, records)
        loser = rejected[0]
        self.assertIn(
            loser['exception_class'], {'IntegrityError', 'UniqueViolation'},
        )
        self.assertEqual(
            loser['sqlstate'], psycopg2.errorcodes.UNIQUE_VIOLATION,
            'losing SQLSTATE must be 23505; records=%r' % records,
        )
        self.assertEqual(loser['sqlstate'], '23505', records)
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'SELECT count(*) FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            self.assertEqual(cr.fetchone()[0], 1)

    def test_existing_evidence_redispatch_commits_on_owned_cursor(self):
        _store_id, job_id = self._durable_fixture()
        token = uuid.uuid4().hex
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            job.sudo().write({
                'state': 'running',
                'current_attempt_token': token,
                'owner_worker_ref': 'owned-redispatch',
                'running_since': fields.Datetime.now(),
            })
            env['shopify.connector.mutation.attempt'].with_context(**{
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': job.job_type,
                'expected_connection_generation':
                    job.store_id.connection_generation,
                'expected_store_identity': job.store_id.shop_domain,
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            Dispatch = env['shopify.connector.job.dispatch']
            with patch.object(
                type(Dispatch), '_transport_mutation_dispatch_selftest',
                side_effect=AssertionError('transport must not replay'),
            ) as transport:
                Dispatch._drain_mutation_one(
                    env['shopify.connector.job'].browse(job_id)
                )
            transport.assert_not_called()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'SELECT state, manual_review_subreason, '
                'current_attempt_token FROM shopify_connector_job '
                'WHERE id = %s',
                (job_id,),
            )
            self.assertEqual(
                cr.fetchone(),
                ('blocked_manual_review', 'duplicate_risk', None),
            )
            cr.execute(
                'SELECT count(*) FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            self.assertEqual(cr.fetchone()[0], 1)

    def test_success_path_commits_c1_c2_then_runs_net_and_fresh_c3(self):
        _store_id, job_id = self._durable_fixture()
        trace = []
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            Dispatch = env['shopify.connector.job.dispatch']
            strategy = dict(Dispatch._get_reconciliation_strategies()[
                'mutation_dispatch_selftest'
            ])
            real = dict(strategy)

            def assert_durable(c2_expected):
                with db_connect(self.env.cr.dbname).cursor() as observer:
                    observer.execute(
                        'SELECT state FROM shopify_connector_job '
                        'WHERE id = %s FOR UPDATE NOWAIT',
                        (job_id,),
                    )
                    self.assertEqual(observer.fetchone()[0], 'running')
                    observer.execute(
                        'SELECT count(*) '
                        'FROM shopify_connector_mutation_attempt '
                        'WHERE job_id = %s',
                        (job_id,),
                    )
                    self.assertEqual(observer.fetchone()[0], c2_expected)
                    if c2_expected:
                        observer.execute(
                            'SELECT id '
                            'FROM shopify_connector_mutation_attempt '
                            'WHERE job_id = %s FOR UPDATE NOWAIT',
                            (job_id,),
                        )
                        self.assertTrue(observer.fetchone()[0])
                    observer.rollback()

            def prepare_local(job):
                trace.append('prepare_local')
                return real['prepare_local'](job)

            def prepare_preconditions(local, owner):
                trace.append('prepare_preconditions')
                assert_durable(0)
                return real['prepare_preconditions'](local, owner)

            def transport(request, context):
                trace.append('transport')
                assert_durable(1)
                return real['transport'](request, context)

            def classify(result):
                trace.append('classify_direct_result')
                return real['classify_direct_result'](result)

            def apply(*args, **kwargs):
                trace.append('apply_consequence')
                return real['apply_consequence'](*args, **kwargs)

            strategy.update({
                'prepare_local': prepare_local,
                'prepare_preconditions': prepare_preconditions,
                'transport': transport,
                'classify_direct_result': classify,
                'apply_consequence': apply,
            })
            with patch.object(
                type(Dispatch), '_get_reconciliation_strategies',
                return_value={'mutation_dispatch_selftest': strategy},
            ):
                Dispatch._drain_mutation_one(
                    env['shopify.connector.job'].browse(job_id)
                )
        self.assertEqual(trace, [
            'prepare_local', 'prepare_preconditions', 'transport',
            'classify_direct_result', 'apply_consequence',
        ])
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'SELECT state FROM shopify_connector_job WHERE id = %s',
                (job_id,),
            )
            self.assertEqual(cr.fetchone()[0], 'succeeded')

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

    def _assert_invalid_recovery_blocks_without_rewrite(self, outcome):
        _store_id, job_id, attempt_id, token = (
            self._durable_owned_attempt(outcome)
        )
        attempt_fields = [
            'attempt_token', 'mutation_domain', 'observed_outcome',
            'resolved_at', 'remote_evidence_refs',
        ]
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            before = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id).read(attempt_fields)[0]
            cr.rollback()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            reconciliation = env[
                'shopify.connector.job.dispatch'
            ]._recover_committed_attempt_to_reconciliation(
                job,
                attempt,
                'post_c2_owner_recovery',
                'dispatcher_recovery',
            )
            self.assertFalse(reconciliation)
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(attempt.observed_outcome, outcome)
            self.assertTrue(attempt.resolved_at)
            self.assertEqual(original.state, 'blocked_manual_review')
            self.assertEqual(
                original.error_class, 'data_shape_schema_mismatch',
            )
            self.assertEqual(
                original.manual_review_subreason, 'duplicate_risk',
            )
            self.assertFalse(original.current_attempt_token)
            self.assertFalse(original.owner_worker_ref)
            self.assertEqual(attempt.read(attempt_fields)[0], before)
            self.assertFalse(env['shopify.connector.job'].search_count([
                ('mutation_attempt_id', '=', attempt_id),
            ]))
            logs = env['shopify.connector.job.log'].search([
                ('job_id', '=', job_id),
                ('to_state', '=', 'blocked_manual_review'),
            ])
            self.assertEqual(len(logs), 1)
            self.assertEqual(
                logs.message,
                'Committed attempt had an invalid recovery state.',
            )
            cr.rollback()

    def test_succeeded_recovery_blocks_without_rewriting_attempt(self):
        self._assert_invalid_recovery_blocks_without_rewrite('succeeded')

    def test_failed_clean_recovery_blocks_without_rewriting_attempt(self):
        self._assert_invalid_recovery_blocks_without_rewrite('failed_clean')

    def test_valid_recovery_still_admits_one_reconciliation(self):
        for outcome in ('pending', 'uncertain'):
            _store_id, job_id, attempt_id, _token = (
                self._durable_owned_attempt(outcome)
            )
            with db_connect(self.env.cr.dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                job = env['shopify.connector.job'].browse(job_id)
                attempt = env[
                    'shopify.connector.mutation.attempt'
                ].browse(attempt_id)
                reconciliation = env[
                    'shopify.connector.job.dispatch'
                ]._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'post_c2_owner_recovery',
                    'dispatcher_recovery',
                )
                self.assertEqual(len(reconciliation), 1)
                self.assertEqual(
                    reconciliation.mutation_attempt_id, attempt,
                )
                self.assertEqual(attempt.observed_outcome, 'uncertain')
                self.assertFalse(attempt.resolved_at)
                self.assertTrue(attempt.remote_evidence_refs['recovery'])
                self.assertFalse(job.current_attempt_token)
                self.assertFalse(job.owner_worker_ref)
                self.assertFalse(job.running_since)
                self.assertEqual(env['shopify.connector.job'].search_count([
                    ('mutation_attempt_id', '=', attempt_id),
                ]), 1)
                cr.commit()

    def test_recovery_user_error_preserves_single_writer_refusal(self):
        _store_id, job_id, attempt_id, token = self._durable_owned_attempt()
        attempt_fields = [
            'attempt_token', 'mutation_domain', 'observed_outcome',
            'resolved_at', 'remote_evidence_refs',
        ]
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            before = attempt.read(attempt_fields)[0]
            with patch.object(
                type(attempt),
                '_record_recovery_uncertain',
                side_effect=UserError(
                    'The mutation attempt is owned by another worker.'
                ),
            ) as recovery:
                reconciliation = env[
                    'shopify.connector.job.dispatch'
                ]._recover_committed_attempt_to_reconciliation(
                    job,
                    attempt,
                    'post_c2_owner_recovery',
                    'dispatcher_recovery',
                )
            recovery.assert_called_once()
            self.assertFalse(reconciliation)
            cr.commit()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            attempt = env[
                'shopify.connector.mutation.attempt'
            ].browse(attempt_id)
            original = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(original.state, 'running')
            self.assertEqual(original.current_attempt_token, token)
            self.assertEqual(attempt.read(attempt_fields)[0], before)
            self.assertFalse(env['shopify.connector.job'].search_count([
                ('mutation_attempt_id', '=', attempt_id),
            ]))
            cr.rollback()

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

    @mute_logger('odoo.sql_db')
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
