import uuid
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models.shopify_connector_job import BUSINESS_JOB_SOURCES

NON_CONNECTED_STATES = ('setup_incomplete', 'reconnect_needed', 'disconnected')


class TestJobEnqueue(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Job Enqueue Test Store',
            'shop_domain': 'job-enqueue-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Enqueue = cls.env['shopify.connector.job.enqueue']
        cls.Job = cls.env['shopify.connector.job']

    def _extra_for(self, job_source):
        if job_source == 'odoo_event':
            return {'trigger_origin': 'inventory_stock_change'}
        return {}

    # ------------------------------------------------------------------
    # 1. Enqueue allowed/blocked by store state.
    # ------------------------------------------------------------------

    def test_enqueue_blocked_when_not_connected(self):
        for state in NON_CONNECTED_STATES:
            self.store.write({'state': state})
            for job_source in BUSINESS_JOB_SOURCES:
                with self.assertRaises(ValidationError):
                    self.Enqueue.enqueue(
                        self.store, job_source, 'core_dispatch_selftest',
                        payload_hash=str(uuid.uuid4()),
                        **self._extra_for(job_source),
                    )

    def test_enqueue_succeeds_when_connected(self):
        self.store.write({'state': 'connected'})
        for job_source in BUSINESS_JOB_SOURCES:
            job = self.Enqueue.enqueue(
                self.store, job_source, 'core_dispatch_selftest',
                payload_hash=str(uuid.uuid4()),
                **self._extra_for(job_source),
            )
            self.assertTrue(job.id)
            self.assertEqual(job.state, 'queued')
            self.assertEqual(job.job_source, job_source)

    def test_enqueue_core_source_never_gated_by_store_state(self):
        for state in NON_CONNECTED_STATES:
            self.store.write({'state': state})
            job = self.Enqueue.enqueue(
                self.store, 'setup_readiness_check',
                'core_dispatch_selftest', payload_hash=str(uuid.uuid4()),
            )
            self.assertTrue(job.id)

    # ------------------------------------------------------------------
    # 2. Enqueue idempotency (existing idempotency_key constraint).
    # ------------------------------------------------------------------

    # mute_logger: the second enqueue() below intentionally triggers the
    # job model's (store_id, idempotency_key) unique-constraint
    # violation; without muting, Odoo's `odoo.sql_db` logger emits an
    # avoidable ERROR-level "bad query" line for this expected failure
    # (mirrors the existing test_core_readiness_check_untouched_still_
    # collides / test_duplicate_credential_row_for_same_store_raises
    # pattern).
    @mute_logger('odoo.sql_db')
    def test_enqueue_idempotency_key_collision_raises(self):
        self.store.write({'state': 'connected'})
        self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='same-hash-value',
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Enqueue.enqueue(
                    self.store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash='same-hash-value',
                )

    def test_enqueue_distinct_payload_hash_does_not_collide(self):
        self.store.write({'state': 'connected'})
        job_1 = self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='hash-a',
        )
        job_2 = self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='hash-b',
        )
        self.assertNotEqual(job_1.idempotency_key, job_2.idempotency_key)

    # ------------------------------------------------------------------
    # 3. Operation-scope duplicate prevention (existing
    # operation_scope_key constraint).
    # ------------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_enqueue_operation_scope_collision_raises(self):
        self.store.write({'state': 'connected'})
        self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='hash-1', res_model='res.partner', res_id=1,
            shopify_target_gid='gid://shopify/Customer/1',
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Enqueue.enqueue(
                    self.store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash='hash-2', res_model='res.partner',
                    res_id=1,
                    shopify_target_gid='gid://shopify/Customer/1',
                )

    def test_enqueue_operation_scope_does_not_collide_for_distinct_targets(self):
        self.store.write({'state': 'connected'})
        job_1 = self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='hash-1', res_model='res.partner', res_id=1,
            shopify_target_gid='gid://shopify/Customer/1',
        )
        job_2 = self.Enqueue.enqueue(
            self.store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash='hash-2', res_model='res.partner', res_id=2,
            shopify_target_gid='gid://shopify/Customer/2',
        )
        self.assertNotEqual(job_1.operation_scope_key, job_2.operation_scope_key)

    # ------------------------------------------------------------------
    # No live Shopify call.
    # ------------------------------------------------------------------

    def test_enqueue_never_calls_shopify_api_client(self):
        Client = self.env['shopify.connector.api.client']

        def _fail_if_called(self, store, query, variables=None):
            raise AssertionError(
                'Enqueue must never call the Shopify API client.'
            )

        self.store.write({'state': 'connected'})
        with patch.object(type(Client), 'execute', _fail_if_called):
            job = self.Enqueue.enqueue(
                self.store, 'manual_sync', 'core_dispatch_selftest',
                payload_hash=str(uuid.uuid4()),
            )
        self.assertTrue(job.id)
