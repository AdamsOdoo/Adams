import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class TestTestConnection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Test Connection Test Store',
            'shop_domain': 'test-connection-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.user_admin = cls._create_group_user(
            'admin', 'group_shopify_connector_admin'
        )

    def setUp(self):
        super().setUp()
        # CORE-R2 (review 4691182306 #1): `action_test_connection` now routes
        # through `_admit_lifecycle`, which captures its one-token snapshot in an
        # OWNED `registry.cursor()` side transaction (store-row FOR SHARE), exactly
        # like business `_admit`. A plain TransactionCase side cursor is a
        # genuinely independent connection that cannot see this class's uncommitted
        # fixture; entering registry test mode makes every `registry.cursor()`
        # reuse the single test connection as a TestCursor so the fixture is
        # visible cross-cursor -- the sanctioned mechanism `TestBusinessAdmission`
        # already uses. Packet-§4 seam-compat: no assertion changed.
        self.env.flush_all()
        self.registry_enter_test_mode()

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Test Connection Test %s' % label,
            'login': 'test_connection_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _set_token(self):
        self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        ).action_set_token(self.store, DUMMY_TOKEN)

    def _get_credential(self):
        return self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        ).search([('store_id', '=', self.store.id)], limit=1)

    def _latest_job(self):
        return self.env['shopify.connector.job'].search(
            [
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'core_test_connection'),
            ],
            order='id desc', limit=1,
        )

    # CORE-R2 (review 4690804619 #1): the lifecycle probe now binds to one
    # credential snapshot and calls `_send(store, body, token)`, so the
    # transport-seam fakes below accept the token argument (they ignore its value;
    # only the arity changed). This is the packet-§4 minimal seam-compat migration
    # of this existing api-client test -- no assertion changed.
    def _run_test_connection(self, fake_send):
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', fake_send):
            return self.store.with_user(self.user_admin).action_test_connection()

    # 20. Pass path: mirrors + snapshot + job/log rows.
    def test_pass_path_writes_mirrors_and_job_log(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertTrue(self.store.last_test_connection_at)
        self.assertFalse(self.store.last_test_connection_reason)
        self.assertTrue(self.store.credential_last_verified_at)
        self.assertEqual(
            json.loads(self.store.granted_scopes), ['read_products']
        )
        self.assertTrue(self.store.granted_scopes_checked_at)
        job = self._latest_job()
        self.assertEqual(job.job_source, 'setup_readiness_check')
        self.assertEqual(job.state, 'succeeded')
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)], order='id asc',
        )
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs.mapped('event_type'), ['attempt', 'attempt'])
        self.assertEqual(logs[1].to_state, 'succeeded')
        # Guards the Odoo 19 job.log.store_id NOT NULL production fix.
        self.assertTrue(all(log.store_id == self.store for log in logs))

    # 21. Identity-mismatch path.
    def test_identity_mismatch_fails_odoo_validation_configuration(self):
        self._set_token()
        response = FakeResponse(
            200,
            json_body=_success_body(domain='different-shop.myshopify.com'),
        )
        credential_before = self._get_credential().credential_state
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'fail')
        job = self._latest_job()
        self.assertEqual(job.error_class, 'odoo_validation_configuration')
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(
            self._get_credential().credential_state, credential_before
        )

    # 22. Missing-credential precondition: fails clean, no HTTP call, no job.
    def test_missing_credential_raises_before_any_send(self):
        send_calls = []

        def fake_send(self, store, body, token=None):
            send_calls.append(1)
            return FakeResponse(200, json_body=_success_body())

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', fake_send):
            with self.assertRaises(UserError):
                self.store.with_user(self.user_admin).action_test_connection()
        self.assertEqual(send_calls, [])
        jobs = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_test_connection'),
        ])
        self.assertFalse(jobs)

    # 23. Auth-failure path: credential_state flips to invalid.
    def test_auth_failure_sets_credential_invalid(self):
        self._set_token()
        response = FakeResponse(200, json_body={
            'errors': [{
                'message': 'Access denied',
                'extensions': {'code': 'ACCESS_DENIED'},
            }],
        })
        self._run_test_connection(lambda self, store, body, token=None: response)
        job = self._latest_job()
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.error_class, 'shopify_permission_scope_auth')
        self.assertEqual(self._get_credential().credential_state, 'invalid')
        # Guards the Odoo 19 job.log.store_id NOT NULL production fix:
        # this failure path's own _system_append() call must still
        # succeed and resolve store_id to the job's store.
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)]
        )
        self.assertTrue(logs)
        self.assertTrue(all(log.store_id == self.store for log in logs))

    # 24. Shop-state-failure path: credential_state never flips (four fixtures).
    def test_shop_state_failure_never_flips_credential_state(self):
        fixtures = [
            FakeResponse(402, text='Payment required'),
            FakeResponse(423, text='Locked'),
            FakeResponse(403, text='Fraudulent'),
            FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'SHOP_INACTIVE'},
                }],
            }),
        ]
        for response in fixtures:
            self._set_token()
            credential_before = self._get_credential().credential_state
            self._run_test_connection(
                lambda self, store, body, token=None, r=response: r
            )
            job = self._latest_job()
            self.assertEqual(job.state, 'failed_final')
            self.assertEqual(job.error_class, 'shopify_permission_scope_auth')
            self.assertEqual(
                self._get_credential().credential_state, credential_before
            )

    # 25. Version fall-forward on an otherwise-passing run.
    def test_version_fallforward_warns_but_still_passes(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain),
            headers={'X-Shopify-API-Version': '2026-10'},
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.api_health_state, 'degraded')
        self.assertTrue(self.store.api_health_reason)

    # 26. Idempotency -- the collision guard: two runs, two distinct nonces.
    def test_second_run_does_not_collide_on_idempotency_key(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        self._run_test_connection(lambda self, store, body, token=None: response)
        jobs = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_test_connection'),
        ])
        self.assertEqual(len(jobs), 2)
        self.assertEqual(len(set(jobs.mapped('payload_hash'))), 2)

    # 27. No secret persisted on store, job, or job.log.
    def test_no_secret_persisted_anywhere(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        job = self._latest_job()
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)]
        )
        # fields_get() here is schema enumeration only (which char/text
        # fields exist), not a security oracle -- the assertion below
        # scans actual field values for token leakage, unrelated to any
        # ACL/visibility check.
        for recordset in (self.store, job, logs):
            fields_info = recordset.fields_get()
            for field_name, info in fields_info.items():
                if info['type'] not in ('char', 'text'):
                    continue
                for rec in recordset:
                    value = rec[field_name]
                    if value:
                        self.assertNotIn(DUMMY_TOKEN, value)

    # 28. core_readiness_check untouched -- documents TD-001, must still collide.
    # mute_logger: this test intentionally triggers the job model's
    # (store_id, idempotency_key) unique-constraint violation (TD-001,
    # not fixed here); without muting, Odoo's `odoo.sql_db` logger emits
    # an avoidable ERROR-level "bad query" line for this expected failure.
    @mute_logger('odoo.sql_db')
    def test_core_readiness_check_untouched_still_collides(self):
        Job = self.env['shopify.connector.job']
        Job.create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_readiness_check',
            'state': 'running',
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                Job.create({
                    'store_id': self.store.id,
                    'job_source': 'setup_readiness_check',
                    'job_type': 'core_readiness_check',
                    'state': 'running',
                })
