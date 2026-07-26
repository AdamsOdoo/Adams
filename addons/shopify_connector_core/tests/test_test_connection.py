import json
import logging
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger

from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'

_logger = logging.getLogger(__name__)


# Stage R1: run post_install. This class creates res.users fixtures; on a build
# where `account` (which adds the required `autopost_bills` field to res.partner)
# loads AFTER shopify_connector_core, an at_install run fails in setUpClass with a
# res_partner NOT-NULL violation before the module's own fields even matter. The
# post_install phase runs after every module (account included) is fully loaded,
# which is the correct phase for role-user security tests.
@tagged('post_install', '-at_install')


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

    # 25. Version fall-forward now FAILS the probe (2026-07-26 ruling).
    #
    # Formerly `test_version_fallforward_warns_but_still_passes`, which
    # asserted `last_test_connection_result == 'pass'` with a `degraded`
    # health state. "Verified, but against a schema we did not check" is the
    # soft disposition the API-version ruling removes: a store served on
    # another version is not a connection this connector can vouch for, so
    # the probe fails with the configuration class and the store is not
    # marked verified.
    def test_version_fallforward_fails_the_probe(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain),
            headers={'X-Shopify-API-Version': '2026-10'},
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'fail')
        self.assertTrue(self.store.last_test_connection_reason)
        job = self._latest_job()
        self.assertEqual(job.error_class, 'odoo_validation_configuration')

    # 25b. A response with no version header fails the probe for the same
    # reason: there is no evidence the schema matched.
    def test_missing_version_header_fails_the_probe(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain),
            headers={},
        )
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'fail')

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

    # 29. Stage R1 P1 -- permission must be enforced BEFORE any side effect.
    # A non-admin caller (Auditor / Operator / Reviewer / plain user) must be
    # denied with AccessError before action_test_connection creates a job or
    # job.log, reads the credential, or reaches the Shopify transport. Pre-fix
    # this test fails for Auditor/Operator/Reviewer (they reach `_send` and
    # create a job because `_run_connection_probe` performs those side effects
    # via sudo() before the late non-sudo store write denies them); the logged
    # per-role table is the recorded runtime proof. Post-fix all roles are
    # denied with zero side effects. The store-write ACL is Admin-only, so the
    # boundary guard uses the existing group_shopify_connector_admin.
    def _role_user(self, label, *role_suffixes):
        groups = 'base.group_user'
        for suffix in role_suffixes:
            groups += ',shopify_connector_core.group_shopify_connector_%s' % suffix
        return new_test_user(
            self.env, login='tc_p1_%s' % label, groups=groups,
        )

    def test_test_connection_denies_non_admin_before_side_effects(self):
        self._set_token()
        Client = self.env['shopify.connector.api.client']
        Job = self.env['shopify.connector.job'].sudo()
        JobLog = self.env['shopify.connector.job.log'].sudo()
        roles = [
            ('auditor', ('auditor',)),
            ('operator', ('operator',)),
            ('reviewer', ('reviewer',)),
            ('plain', ()),
        ]
        evidence = []
        for label, suffixes in roles:
            user = self._role_user(label, *suffixes)
            send = []

            def fake_send(inner_self, store, body, token=None, _s=send):
                _s.append(1)
                return FakeResponse(
                    200,
                    json_body=_success_body(domain=self.store.shop_domain),
                )

            jobs0 = Job.search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'core_test_connection'),
            ])
            logs0 = JobLog.search_count([('store_id', '=', self.store.id)])
            tc_at0 = self.store.last_test_connection_at
            cred0 = self._get_credential().credential_state
            exc = 'NONE(success)'
            with patch.object(type(Client), '_send', fake_send):
                try:
                    self.store.with_user(user).action_test_connection()
                except Exception as e:  # noqa: BLE001 -- observing the raise
                    exc = type(e).__name__
            self.env.invalidate_all()
            djob = Job.search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'core_test_connection'),
            ]) - jobs0
            dlog = JobLog.search_count(
                [('store_id', '=', self.store.id)]) - logs0
            self.store.invalidate_recordset()
            evidence.append((
                label, exc, len(send), djob, dlog,
                self.store.last_test_connection_at != tc_at0,
                self._get_credential().credential_state != cred0,
            ))

        for row in evidence:
            _logger.info(
                'P1 test_connection role=%-9s exc=%-18s send=%s dJob=%s '
                'dLog=%s storeChanged=%s credChanged=%s', *row)

        for label, exc, send_n, djob, dlog, store_changed, cred_changed in evidence:
            self.assertEqual(
                exc, 'AccessError',
                '%s: expected AccessError, got %s' % (label, exc))
            self.assertEqual(
                send_n, 0,
                '%s reached the Shopify transport before denial' % label)
            self.assertEqual(
                djob, 0, '%s created a job before denial' % label)
            self.assertEqual(
                dlog, 0, '%s created a job log before denial' % label)
            self.assertFalse(
                store_changed, '%s mutated a store mirror before denial' % label)
            self.assertFalse(
                cred_changed,
                '%s mutated the credential before denial' % label)

    # 30. Admin path is unchanged by the boundary guard (regression).
    def test_test_connection_admin_still_succeeds_after_guard(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain))
        self._run_test_connection(lambda self, store, body, token=None: response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        job = self._latest_job()
        self.assertEqual(job.state, 'succeeded')
