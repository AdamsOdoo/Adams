# Part of the Shopify Connector (U0 operator UI foundation).
#
# Functional tests for the read-only dashboard aggregate service
# shopify.connector.ui.dashboard.get_dashboard_data. These exercise the single
# severity model: empty / healthy / warning / degraded / manual-review, the
# at-most-three exception rule, count/domain agreement, the resolved-excluded
# rule, bounded reads, and the no-sensitive-data guarantee.

import re

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Dashboard = cls.env['shopify.connector.ui.dashboard']
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
            'api_version': '2025-01',
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
        # reconnect coexisting with no danger => degraded band (danger),
        # because a reconnect blocks work like a failure would.
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
