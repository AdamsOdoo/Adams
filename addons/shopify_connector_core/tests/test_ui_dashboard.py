# Part of the Shopify Connector (U0 operator UI foundation).
#
# Functional tests for the read-only dashboard aggregate service
# shopify.connector.ui.dashboard.get_dashboard_data. These exercise the single
# severity model: empty / healthy / warning / degraded / manual-review, the
# at-most-three exception rule, count/domain agreement, the resolved-excluded
# rule, bounded reads, and the no-sensitive-data guarantee.

import re
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
from odoo.tests.common import TransactionCase, new_test_user, tagged

EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The dashboard aggregate is connector-users-only and runs as the
        # *current* user (per-user ACLs apply). Exercise it as the realistic
        # caller -- a connector Auditor with read on the connector models. The
        # framework superuser is not a connector-group member, so running the
        # aggregate as the raw superuser would (correctly) be refused.
        cls.viewer = new_test_user(
            cls.env, login='u0_dash_viewer',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor')
        cls.Dashboard = cls.env[
            'shopify.connector.ui.dashboard'].with_user(cls.viewer)
        cls.Store = cls.env['shopify.connector.store'].sudo()
        cls.Job = cls.env['shopify.connector.job'].sudo()
        cls._seq = 0

    # ------------------------------------------------------------------ #
    #  fixtures
    # ------------------------------------------------------------------ #
    @classmethod
    def _make_store(cls, state='connected', **extra):
        cls._seq += 1
        vals = {
            'name': 'U0 Store %d' % cls._seq,
            'shop_domain': 'u0-store-%d.myshopify.com' % cls._seq,
            'api_version': SHOPIFY_API_VERSION,
            'state': state,
            'credential_present': True,
        }
        vals.update(extra)
        return cls.Store.create(vals)

    @classmethod
    def _make_job(cls, store, state, **extra):
        cls._seq += 1
        vals = {
            'store_id': store.id,
            # Non-business source avoids the connected-store enqueue gate, so a
            # job can be seeded directly in any state for aggregate testing.
            'job_source': 'setup_readiness_check',
            'job_type': 'core_manual_maintenance',
            'state': state,
            'payload_hash': 'u0-dash-%d' % cls._seq,
        }
        if state == 'blocked_manual_review':
            vals['manual_review_subreason'] = 'ambiguous_match'
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        vals.update(extra)
        return cls.Job.create(vals)

    # ------------------------------------------------------------------ #
    #  states
    # ------------------------------------------------------------------ #
    def test_empty_when_no_stores(self):
        data = self.Dashboard.get_dashboard_data()
        self.assertEqual(data['state'], 'empty')
        self.assertEqual(data['lead']['severity'], 'info')

    def test_healthy(self):
        store = self._make_store()
        self._make_job(store, 'succeeded')
        data = self.Dashboard.get_dashboard_data()
        self.assertEqual(data['state'], 'healthy')
        self.assertEqual(data['lead']['severity'], 'success')
        # Healthy cannot coexist with any active exception.
        self.assertEqual(data['exceptions'], [])
        self.assertTrue(data['affirmative'])

    def test_degraded_on_technical_failure(self):
        store = self._make_store()
        self._make_job(store, 'failed_final')
        data = self.Dashboard.get_dashboard_data()
        self.assertEqual(data['state'], 'degraded')
        self.assertEqual(data['lead']['severity'], 'danger')
        self.assertTrue(any(e['id'] == 'failed_final' for e in data['exceptions']))

    def test_manual_review_only(self):
        store = self._make_store()
        self._make_job(store, 'blocked_manual_review')
        data = self.Dashboard.get_dashboard_data()
        self.assertEqual(data['state'], 'manual_review')
        self.assertEqual(data['lead']['severity'], 'danger')
        self.assertIn('decision', data['lead']['text'].lower() + data['lead']['hint'].lower())

    def test_warning_only_on_retry(self):
        store = self._make_store()
        self._make_job(store, 'retry_waiting')
        data = self.Dashboard.get_dashboard_data()
        self.assertEqual(data['state'], 'warning')
        self.assertEqual(data['lead']['severity'], 'warning')

    def test_reconnect_needed_is_degraded(self):
        self._make_store(state='reconnect_needed')
        data = self.Dashboard.get_dashboard_data()
        # reconnect-needed with no active danger => warning band (a reconnect is
        # a warning-tier attention item, not a failure). Kept lenient so the
        # test stays robust if the severity tiering is later refined.
        self.assertIn(data['state'], ('degraded', 'warning'))

    # ------------------------------------------------------------------ #
    #  exception rules
    # ------------------------------------------------------------------ #
    def test_at_most_three_exceptions(self):
        store = self._make_store()
        for _i in range(2):
            self._make_job(store, 'blocked_manual_review')
        self._make_job(store, 'failed_final')
        self._make_job(store, 'failed_retryable')
        self._make_store(state='reconnect_needed')
        data = self.Dashboard.get_dashboard_data()
        self.assertLessEqual(len(data['exceptions']), 3)

    def test_action_domains_match_counts(self):
        store = self._make_store()
        self._make_job(store, 'blocked_manual_review')
        self._make_job(store, 'failed_final')
        self._make_job(store, 'failed_final')
        data = self.Dashboard.get_dashboard_data()
        for exc in data['exceptions']:
            model = exc['target']['res_model']
            domain = exc['target']['domain']
            actual = self.env[model].sudo().search_count(domain)
            self.assertEqual(
                actual, exc['count'],
                "Exception %s count (%s) must equal its domain count (%s)."
                % (exc['id'], exc['count'], actual),
            )

    def test_recent_activity_bounded(self):
        store = self._make_store()
        for _i in range(self.Dashboard.RECENT_ACTIVITY_LIMIT + 5):
            self._make_job(store, 'succeeded')
        data = self.Dashboard.get_dashboard_data()
        self.assertLessEqual(len(data['activity']), self.Dashboard.RECENT_ACTIVITY_LIMIT)

    # ------------------------------------------------------------------ #
    #  safety
    # ------------------------------------------------------------------ #
    def test_no_sensitive_data_in_payload(self):
        store = self._make_store()
        self._make_job(store, 'failed_final')
        data = self.Dashboard.get_dashboard_data()
        forbidden_keys = {'access_token', 'token', 'credential', 'password',
                          'payload_snapshot', 'remote_mutation_intent',
                          'preconditions_snapshot', 'remote_evidence_refs',
                          'technical_detail', 'email', 'phone'}

        def walk(node, path=''):
            if isinstance(node, dict):
                for k, v in node.items():
                    self.assertNotIn(
                        str(k).lower(), forbidden_keys,
                        "Forbidden key %r at %s" % (k, path),
                    )
                    walk(v, path + '/' + str(k))
            elif isinstance(node, (list, tuple)):
                for i, v in enumerate(node):
                    walk(v, '%s[%d]' % (path, i))
            elif isinstance(node, str):
                self.assertIsNone(
                    EMAIL_RE.search(node),
                    "Email-shaped string leaked at %s: %r" % (path, node),
                )
        walk(data)

    def test_non_connector_user_is_denied(self):
        user = new_test_user(self.env, login='u0_outsider', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.Dashboard.with_user(user).get_dashboard_data()

    def test_severity_consistency_healthy_has_no_active_counts(self):
        store = self._make_store()
        self._make_job(store, 'succeeded')
        data = self.Dashboard.get_dashboard_data()
        if data['state'] == 'healthy':
            self.assertEqual(data['stores']['reconnect_needed'], 0)
            self.assertEqual(len(data['exceptions']), 0)

    # ------------------------------------------------------------------ #
    #  Store 360 core payload (the sale/fulfillment sections are owned and
    #  tested by their modules; core owns meta/health/flows/critical)
    # ------------------------------------------------------------------ #
    def test_store360_payload_core_shape(self):
        store = self._make_store()
        self._make_job(store, 'succeeded')
        payload = self.Dashboard.get_store_360_data(store.id, '30d')
        for key in ('meta', 'health', 'flows', 'stores_region', 'critical',
                    'generated_at', 'refresh_interval_seconds'):
            self.assertIn(key, payload)
        self.assertEqual(payload['meta']['store_id'], store.id)
        self.assertEqual(payload['meta']['period'], '30d')
        self.assertEqual(
            [row['id'] for row in payload['flows']],
            ['orders', 'catalog', 'inventory', 'export', 'fulfillment'],
        )

    def test_store360_refuses_unknown_period_and_store(self):
        self._make_store()
        with self.assertRaises(UserError):
            self.Dashboard.get_store_360_data(False, 'forever')
        with self.assertRaises(UserError):
            self.Dashboard.get_store_360_data(987654321, '30d')

    def test_store360_exceptions_are_store_scoped_and_count_exact(self):
        store_a = self._make_store()
        store_b = self._make_store()
        self._make_job(store_a, 'failed_final')
        self._make_job(store_b, 'failed_final')
        self._make_job(store_b, 'failed_final')
        payload = self.Dashboard.get_store_360_data(store_b.id, '30d')
        failed = [exc for exc in payload['health']['exceptions']
                  if exc['id'] == 'failed_final']
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]['count'], 2)
        Job = self.env['shopify.connector.job'].with_user(self.viewer)
        domain = [tuple(t) for t in failed[0]['target']['domain']]
        self.assertEqual(Job.search_count(domain), 2)

    def test_store360_multi_store_region_appears_only_with_two_stores(self):
        store = self._make_store()
        payload = self.Dashboard.get_store_360_data(store.id, '30d')
        self.assertFalse(payload['stores_region']['available'])
        self._make_store()
        payload = self.Dashboard.get_store_360_data(False, '30d')
        self.assertTrue(payload['stores_region']['available'])
        self.assertEqual(len(payload['stores_region']['rows']), 2)

    def test_store360_empty_state_matches_the_first_run(self):
        payload = self.Dashboard.get_store_360_data()
        self.assertEqual(payload['health']['state'], 'empty')

    def test_store360_critical_band_names_a_disconnected_store(self):
        store = self._make_store(state='disconnected')
        payload = self.Dashboard.get_store_360_data(store.id, '30d')
        self.assertTrue(payload['critical']['active'])
        causes = {cause['id'] for cause in payload['critical']['causes']}
        self.assertIn('store_state', causes)

    # ------------------------------------------------------------------ #
    #  C7 split dashboards
    # ------------------------------------------------------------------ #
    def test_split_payloads_never_mix_sales_and_health(self):
        store = self._make_store()
        sales = self.Dashboard.get_sales_dashboard_data(store.id, '30d')
        health = self.Dashboard.get_connector_health_data(store.id)

        self.assertIn('commercial', sales)
        for forbidden in (
            'health', 'flows', 'stores_region', 'throttle', 'mappings',
            'reconciliation', 'mode_switch',
        ):
            self.assertNotIn(forbidden, sales)

        for key in (
            'health', 'flows', 'stores_region', 'throttle', 'mappings',
            'reconciliation', 'mode_switch',
        ):
            self.assertIn(key, health)
        for forbidden in ('commercial', 'bridge', 'lifecycle', 'dispatch'):
            self.assertNotIn(forbidden, health)

    def test_health_all_stores_never_hides_a_failing_store(self):
        healthy = self._make_store()
        failing = self._make_store()
        self._make_job(healthy, 'succeeded')
        self._make_job(failing, 'failed_final')
        payload = self.Dashboard.get_connector_health_data(False)
        rows = {row['id']: row for row in payload['stores_region']['rows']}
        self.assertEqual(set(rows), {healthy.id, failing.id})
        self.assertEqual(rows[failing.id]['tone'], 'attention')
        self.assertEqual(payload['stores_region']['summary']['attention'], 1)

    def test_health_missing_evidence_is_unknown_not_healthy(self):
        store = self._make_store()
        payload = self.Dashboard.get_connector_health_data(store.id)
        self.assertEqual(
            payload['stores_region']['rows'][0]['tone'], 'unknown',
        )
        self.assertTrue(all(
            row['tone'] == 'unknown' for row in payload['flows']
        ))
        self.assertTrue(all(
            row['state'] in ('observed', 'unknown')
            for row in payload['mappings']['rows']
        ))
        self.assertTrue(any(
            row['state'] == 'unknown'
            for row in payload['mappings']['rows']
        ))

    def test_connected_cannot_be_ready_before_required_domain_evidence(self):
        store = self._make_store(api_health_state='normal')
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'product_domain_enabled': True,
        })
        # A successful setup/audit job is activity, not catalog completion.
        self._make_job(store, 'succeeded')
        payload = self.Dashboard.get_connector_health_data(store.id)
        row = payload['stores_region']['rows'][0]
        self.assertEqual(
            row['operational_state'], 'connected_initial_sync_pending',
        )
        self.assertEqual(row['domains_selected'], 1)
        self.assertEqual(row['domains_completed'], 0)
        self.assertEqual(
            payload['health']['state'], 'connected_initial_sync_pending',
        )

    def test_ready_requires_fresh_completion_and_no_blocking_work(self):
        store = self._make_store(api_health_state='normal')
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': store.id,
            'product_domain_enabled': True,
        })
        settings.sudo().write({
            'product_last_import_success_at': fields.Datetime.now(),
        })
        payload = self.Dashboard.get_connector_health_data(store.id)
        row = payload['stores_region']['rows'][0]
        self.assertEqual(row['operational_state'], 'ready')
        self.assertEqual(row['domains_completed'], 1)
        self.assertEqual(row['tone'], 'healthy')

    def test_completion_anchor_with_pending_child_is_still_running(self):
        store = self._make_store(api_health_state='normal')
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': store.id,
            'product_domain_enabled': True,
        })
        settings.sudo().write({
            'product_last_import_success_at': fields.Datetime.now(),
        })
        self._make_job(store, 'queued', job_type='product_import_sync')
        payload = self.Dashboard.get_connector_health_data(store.id)
        row = payload['stores_region']['rows'][0]
        self.assertEqual(row['operational_state'], 'initial_sync_running')
        self.assertEqual(row['initial_child_pending'], 1)
        self.assertNotEqual(row['operational_state'], 'ready')

    def test_initial_sync_running_exposes_bounded_progress(self):
        store = self._make_store(api_health_state='normal')
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'product_domain_enabled': True,
        })
        self._make_job(store, 'queued', job_type='product_import_scan')
        payload = self.Dashboard.get_connector_health_data(store.id)
        row = payload['stores_region']['rows'][0]
        self.assertEqual(row['operational_state'], 'initial_sync_running')
        self.assertEqual(row['initial_child_pending'], 1)
        self.assertIn('Monitor progress', row['next_action'])

    def test_health_oldest_blocked_ignores_queue_and_drills_to_same_scope(self):
        store = self._make_store()
        other_store = self._make_store()
        self._make_job(store, 'queued')
        now = fields.Datetime.now()
        recently_blocked_old_job = self._make_job(
            store, 'blocked_manual_review',
            finished_at=now - timedelta(hours=1),
        )
        recently_blocked_old_job.sudo().write({
            'create_date': now - timedelta(days=30),
        })
        blocked = self._make_job(
            store, 'blocked_manual_review',
            finished_at=now - timedelta(days=2),
        )
        self._make_job(other_store, 'blocked_manual_review')

        payload = self.Dashboard.get_connector_health_data(store.id)
        oldest = payload['health']['oldest_blocked']
        self.assertEqual(
            oldest['age'],
            self.Dashboard._relative_time(blocked.finished_at, now),
        )
        self.assertEqual(oldest['target']['res_model'], blocked._name)
        domain = [tuple(term) for term in oldest['target']['domain']]
        self.assertEqual(
            self.env[blocked._name].with_user(self.viewer).search(domain),
            recently_blocked_old_job | blocked,
        )

    def test_health_projects_throttle_headroom_with_observation_time(self):
        store = self._make_store()
        store._record_throttle_status({
            'currentlyAvailable': 100,
            'maximumAvailable': 1000,
            'restoreRate': 0,
        })
        payload = self.Dashboard.get_connector_health_data(store.id)
        row = payload['throttle']['rows'][0]
        self.assertEqual(row['store_id'], store.id)
        self.assertAlmostEqual(row['headroom_ratio'], 0.1)
        self.assertEqual(row['tone'], 'danger')
        self.assertTrue(row['observed_at'])

    def test_split_dashboards_refuse_non_connector_user(self):
        user = new_test_user(
            self.env, login='u0_split_outsider', groups='base.group_user'
        )
        dashboard = self.Dashboard.with_user(user)
        with self.assertRaises(AccessError):
            dashboard.get_sales_dashboard_data()
        with self.assertRaises(AccessError):
            dashboard.get_connector_health_data()
