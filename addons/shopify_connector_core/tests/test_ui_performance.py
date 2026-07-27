# Part of the Shopify Connector (U0 operator UI foundation).
#
# Performance-contract tests (PB-2/PB-8/PB-9/PB-10/PB-11). These prove the
# dashboard aggregate path is bounded and CONSTANT in query count regardless of
# data volume (so it cannot degrade super-linearly), reads no unbounded
# recordset, and honours the explicit recent-activity limit. Absolute p75
# timings against RD-1/RD-2 are captured in the Odoo.sh runtime campaign; here
# a wall-clock smoke bound is recorded.

import os
import time

from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiPerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Exercise the connector-users-only dashboard aggregate as a connector
        # Auditor (the realistic caller); the framework superuser is not a
        # connector-group member. Query-count/timing bounds are unaffected.
        cls.viewer = new_test_user(
            cls.env, login='u0_perf_viewer',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor')
        cls.Dashboard = cls.env[
            'shopify.connector.ui.dashboard'].with_user(cls.viewer)
        cls.Store = cls.env['shopify.connector.store'].sudo()
        cls.Job = cls.env['shopify.connector.job'].sudo()
        cls._seq = 0
        cls.store = cls._make_store()

    @classmethod
    def _make_store(cls):
        cls._seq += 1
        return cls.Store.create({'name': 'P%d' % cls._seq,
                                 'shop_domain': 'u0-perf-%d.myshopify.com' % cls._seq,
                                 'api_version': SHOPIFY_API_VERSION, 'state': 'connected',
                                 'credential_present': True})

    def _seed_jobs(self, n, state='succeeded'):
        vals = []
        for _i in range(n):
            self.__class__._seq += 1
            vals.append({'store_id': self.store.id, 'job_source': 'setup_readiness_check',
                         'job_type': 'core_manual_maintenance', 'state': state,
                         'payload_hash': 'u0-perf-%d' % self._seq,
                         'finished_at': fields.Datetime.now()})
        self.Job.create(vals)
        # Flush the fixture before anything is measured.
        #
        # Odoo defers stored-field recomputation to the next flush, and the next
        # flush is whatever the test does afterwards. Without this line the
        # pending recompute of the jobs just created (SEC-3 #197 added a stored
        # related `company_id` on the job) is charged to the *dashboard* call,
        # and the query count appears to grow with data volume: 17 -> 19, where
        # both extra queries are `UPDATE shopify_connector_job SET company_id`.
        #
        # That is fixture cost, not dashboard cost -- the invariant this class
        # exists to protect is that the dashboard's aggregate READ path is
        # constant. Jobs are created by the dispatcher in their own
        # transactions, so a real dashboard reader never pays a pending seed
        # flush. The assertion below stays strict equality; it is the
        # measurement window that is corrected, not the bound.
        self.env.flush_all()

    def _count_queries(self, fn):
        cr = self.env.cr
        original = cr.execute
        counter = {'n': 0}

        def counting(*args, **kwargs):
            counter['n'] += 1
            return original(*args, **kwargs)

        cr.execute = counting
        try:
            fn()
        finally:
            cr.execute = original
        return counter['n']

    # ------------------------------------------------------------------ #
    def test_dashboard_query_count_bounded(self):
        self._seed_jobs(50)
        n = self._count_queries(lambda: self.Dashboard.get_dashboard_data())
        # A constant handful of indexed count queries + one bounded read.
        self.assertLessEqual(n, 60, "Dashboard issued %d queries; expected a small constant." % n)

    def test_dashboard_query_count_constant_across_scale(self):
        # No week-old jobs, so the sparkline stays unavailable in both passes
        # and the query path is deterministic.
        self._seed_jobs(20)
        # Warm one call first so ORM field metadata / group-resolution one-time
        # work does not inflate the first measured pass (keeps the strict
        # equality assertion meaningful).
        self.Dashboard.get_dashboard_data()
        small = self._count_queries(lambda: self.Dashboard.get_dashboard_data())
        self._seed_jobs(200)
        large = self._count_queries(lambda: self.Dashboard.get_dashboard_data())
        self.assertEqual(
            small, large,
            "Dashboard query count grew with data volume (%d -> %d): super-linear risk." % (small, large),
        )

    def test_recent_activity_respects_explicit_limit(self):
        self._seed_jobs(self.Dashboard.RECENT_ACTIVITY_LIMIT + 30)
        data = self.Dashboard.get_dashboard_data()
        self.assertLessEqual(len(data['activity']), self.Dashboard.RECENT_ACTIVITY_LIMIT)

    def test_dashboard_source_uses_bounded_reads(self):
        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src = open(os.path.join(addon_root, 'models', 'shopify_connector_ui_dashboard.py'),
                   encoding='utf-8').read()
        # The only full record read is the recent-activity search_read, which
        # must carry an explicit limit.
        self.assertIn('search_read(', src)
        self.assertIn('limit=self.RECENT_ACTIVITY_LIMIT', src)
        # No unbounded model.search([]) returning a full recordset for reads.
        self.assertNotIn('.search([])', src)

    def test_dashboard_smoke_timing(self):
        self._seed_jobs(100)
        start = time.perf_counter()
        self.Dashboard.get_dashboard_data()
        elapsed = time.perf_counter() - start
        # Generous smoke bound only; real PB-2 p75 is a runtime measurement.
        self.assertLess(elapsed, 5.0, "Dashboard render took %.3fs (smoke bound 5s)." % elapsed)
