from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the identical note in
# test_lifecycle_uninstall.py. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestPackagePauseGates(TransactionCase):
    """Wave 5 single-package lifecycle: proves the global execution-boundary
    gate (Section 10) actually fires, at every instrumented seam, when the
    package is dependency-paused -- and does NOT fire when it is healthy.

    Forces the paused state directly on the package singleton (an ordinary
    ORM write, not a real module uninstall -- see test_package_lifecycle.py
    for why that is the correct, safe way to exercise this in a
    TransactionCase). The REAL end-to-end proof that a genuine standard-
    dependency loss produces this same state is the disposable-database
    harness (tools/shopify_connector_package_lifecycle_check.py).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Pause Gate Test Store',
            'shop_domain': 'pause-gate-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Package = cls.env['shopify.connector.package']
        cls.Enqueue = cls.env['shopify.connector.job.enqueue']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Job = cls.env['shopify.connector.job']
        cls.Client = cls.env['shopify.connector.api.client']

    def setUp(self):
        super().setUp()
        # `assert_healthy` persists via an independent `registry.cursor()`
        # side transaction (see `shopify_connector_package.py::
        # _commit_via_side_cursor` -- the same CORE-R2 pattern
        # `_admit_lifecycle` already uses). `_force_paused` below writes the
        # SAME package row through the ordinary (uncommitted) test
        # transaction first; without test mode, the side cursor would be a
        # genuinely separate connection and would hang forever waiting for
        # a row lock the test itself is holding. Registry test mode makes
        # every `registry.cursor()` reuse this single test connection
        # instead (the same fix `test_api_client.py` applies for the
        # identical reason).
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _force_paused(self):
        record = self.Package._get_singleton()
        record.sudo().write({
            'state': 'dependency_paused',
            'missing_standard_apps': 'Inventory',
        })
        return record

    def _assert_paused_refusal(self, callable_):
        with self.assertRaises(UserError) as cm:
            callable_()
        self.assertIn('paused', str(cm.exception))

    # -- Healthy positive control -------------------------------------

    def test_enqueue_succeeds_when_healthy(self):
        job = self.Enqueue.enqueue(
            self.store, 'setup_readiness_check', 'core_dispatch_selftest',
        )
        self.assertTrue(job)
        self.assertEqual(job.state, 'queued')

    def test_run_drain_does_not_raise_when_healthy(self):
        self.Dispatch.run_drain(limit=0)

    # -- Paused: every gate must refuse, before any side effect --------

    def test_enqueue_is_blocked_when_paused(self):
        self._force_paused()
        before = self.Job.search_count([])
        self._assert_paused_refusal(lambda: self.Enqueue.enqueue(
            self.store, 'setup_readiness_check', 'core_dispatch_selftest',
        ))
        self.assertEqual(
            self.Job.search_count([]), before,
            "no job row may be created while the package is paused",
        )

    def test_run_drain_is_blocked_when_paused(self):
        self._force_paused()
        self._assert_paused_refusal(lambda: self.Dispatch.run_drain())

    def test_execute_is_blocked_before_any_transport_call_when_paused(self):
        self._force_paused()

        def fail_if_called(self_client, store, body, *extra):
            self.fail('execute() must be gated before _send is ever reached')

        from unittest.mock import patch
        with patch.object(type(self.Client), '_send', fail_if_called):
            self._assert_paused_refusal(
                lambda: self.Client.execute(self.store, 'query { shop { id } }')
            )

    def test_execute_business_is_blocked_before_admission_when_paused(self):
        self._force_paused()

        def fail_if_called(self_client, *args, **kwargs):
            self.fail(
                'execute_business() must be gated before _admit is ever reached'
            )

        from unittest.mock import patch
        with patch.object(type(self.Client), '_admit', fail_if_called):
            job = self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'core_dispatch_selftest',
                'state': 'queued',
                'payload_hash': 'pause-gate-test-hash',
            })
            with self.assertRaises(UserError) as cm:
                with self.Client.execute_business(
                    job, self.store, 'query { shop { id } }',
                ):
                    pass
            self.assertIn('paused', str(cm.exception))

    def test_test_connection_is_blocked_when_paused(self):
        self._force_paused()
        self._assert_paused_refusal(
            lambda: self.store.action_test_connection()
        )

    def test_reconnect_is_blocked_when_paused(self):
        self._force_paused()
        self._assert_paused_refusal(lambda: self.store.action_reconnect())

    def test_activate_is_blocked_when_paused(self):
        self._force_paused()
        self._assert_paused_refusal(lambda: self.store.action_activate())
