import threading
import uuid

from odoo import SUPERUSER_ID, api
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


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
            })
            job = env['shopify.connector.job'].sudo().create({
                'store_id': store.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'mutation_dispatch_selftest',
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
                'DELETE FROM shopify_connector_job_log WHERE job_id = %s',
                (job_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE id = %s',
                (job_id,),
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
