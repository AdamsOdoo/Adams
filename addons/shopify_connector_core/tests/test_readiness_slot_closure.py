import ast
import os
import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from .test_api_client import FakeResponse, _success_body
from .test_credential_service import core_sudo_inventory_for_file

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
DRAIN_CRON_XMLID = (
    'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain'
)
WEBHOOK_HMAC_NA_REASON = (
    'Not applicable — webhook intake is not installed; '
    'scheduled/manual sync is the active trigger mechanism.'
)


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestReadinessSlotClosure(TransactionCase):
    """Task CORE-R1 -- capability-aware readiness correction (D-R1-1..5).

    Proves, through real merged model behavior (never fixture
    force-writes of readiness results or store state), that the three
    formerly-permanent-`not_proven` slots (`cron_queue_health`,
    `mapped_location`, `webhook_hmac`) become capability-aware, that a
    fully successful non-fall-forward test connection records
    `api_health_state='normal'` (D-R1-5), and that an eligible Lite store
    can therefore aggregate `pass` and reach `connected` via
    `action_activate` while fail-closed behavior is preserved for every
    genuine failure.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ReadinessCheck = cls.env['shopify.connector.readiness.check']
        cls.Job = cls.env['shopify.connector.job']
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.store = cls._make_store('base')
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
        # fixtures; entering registry test mode makes every `registry.cursor()`
        # reuse the single test connection as a TestCursor so the fixtures are
        # visible cross-cursor -- the sanctioned mechanism `TestBusinessAdmission`
        # already uses. Packet-§4 seam-compat: no assertion changed;
        # `action_activate` and the source-guard tests open no side cursor, so test
        # mode is transparent to them.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # Fixtures / helpers
    # ------------------------------------------------------------------

    @classmethod
    def _make_store(cls, slug):
        return cls.env['shopify.connector.store'].create({
            'name': 'CORE-R1 %s' % slug,
            'shop_domain': 'core-r1-%s.myshopify.com' % slug,
            'api_version': '2026-07',
        })

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'CORE-R1 Slot Closure %s' % label,
            'login': 'core_r1_slot_closure_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _make_queued_job(
        self, store, age_minutes=0, started_at=None, state='queued',
        job_type='core_manual_maintenance',
    ):
        """Create a job for `store`, optionally back-dating its
        `create_date` (SQL -- `create_date` is a log-access magic field)
        and/or setting a historical `started_at` (ORM).

        `job_source='setup_readiness_check'` keeps creation ungated by
        the Task 005 business-source store-state gate; a fresh UUID4
        `payload_hash` keeps the idempotency key unique.
        """
        job = self.Job.create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        })
        if started_at is not None:
            job.write({'started_at': started_at})
        if age_minutes:
            old = fields.Datetime.now() - timedelta(minutes=age_minutes)
            self.env.cr.execute(
                'UPDATE shopify_connector_job SET create_date = %s '
                'WHERE id = %s',
                (old, job.id),
            )
            job.invalidate_recordset()
        return job

    def _set_token(self, store):
        self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        ).action_set_token(store, DUMMY_TOKEN)

    def _scope_body(self, domain, scopes):
        return {
            'data': {
                'shop': {
                    'id': 'gid://shopify/Shop/1',
                    'name': 'CORE-R1 Shop',
                    'myshopifyDomain': domain,
                },
                'currentAppInstallation': {
                    'accessScopes': [{'handle': s} for s in scopes],
                },
            },
        }

    def _run_test_connection(self, store, response):
        # CORE-R2 (review 4690804619 #1): the lifecycle probe passes its one token
        # snapshot to `_send(store, body, token)`; the transport-seam fake accepts
        # the token argument (packet-§4 minimal seam-compat, no assertion changed).
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), '_send', lambda self, s, body, token=None: response
        ):
            store.with_user(self.user_admin).action_test_connection()

    def _provision_ready_lite_store(self, slug, scopes=None):
        """Provision an activate-eligible Lite store (core + product +
        sale, no inventory) entirely through real merged behavior: set
        credential, https base URL, product/sale domain flags, and a real
        (mocked-transport) successful non-fall-forward test connection
        that records granted scopes + `api_health_state='normal'`.

        No readiness result and no store state is force-written here.
        """
        if scopes is None:
            scopes = list(self.ReadinessCheck.REQUIRED_MVP_SCOPES)
        store = self._make_store(slug)
        self._set_token(store)
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://core-r1.example.test'
        )
        self.Settings.create({
            'store_id': store.id,
            'product_domain_enabled': True,
            'sale_domain_enabled': True,
        })
        self._run_test_connection(
            store, FakeResponse(
                200, json_body=self._scope_body(store.shop_domain, scopes)
            )
        )
        store.invalidate_recordset()
        return store

    # ==================================================================
    # D-R1-1 -- cron_queue_health
    # ==================================================================

    # 1. Active drain cron + empty queue -> pass.
    def test_cron_queue_health_active_cron_empty_queue_passes(self):
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'pass')

    # 2. Missing drain cron -> named failure.
    def test_cron_queue_health_missing_cron_named_failure(self):
        with patch.object(
            type(self.ReadinessCheck), '_drain_cron_active_state',
            lambda self: None,
        ):
            check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'fail')
        self.assertIn('missing', check['reason'].lower())

    # 3. Inactive drain cron -> named failure (real sudo read of the
    #    deactivated cron record).
    def test_cron_queue_health_inactive_cron_named_failure(self):
        self.env.ref(DRAIN_CRON_XMLID).sudo().write({'active': False})
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'fail')
        self.assertIn('inactive', check['reason'].lower())

    # 4. Queued job older than the threshold with no started_at -> named
    #    failure using the exact discriminator.
    def test_cron_queue_health_stalled_queued_job_named_failure(self):
        self._make_queued_job(self.store, age_minutes=61)
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'fail')
        self.assertIn('stalled', check['reason'].lower())
        self.assertIn('60', check['reason'])

    # 4b. A recently-queued job (under the threshold) is not stalled.
    def test_cron_queue_health_recent_queued_job_not_stalled(self):
        self._make_queued_job(self.store, age_minutes=30)
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'pass')

    # 5. A dispatched (running) or cancelled old job no longer blocks
    #    readiness -- the discriminator is state='queued' only.
    def test_cron_queue_health_dispatched_or_cancelled_job_does_not_block(self):
        self._make_queued_job(
            self.store, age_minutes=120, state='cancelled',
        )
        self._make_queued_job(
            self.store, age_minutes=120, state='running',
            started_at=fields.Datetime.now() - timedelta(minutes=119),
        )
        self._make_queued_job(self.store, age_minutes=120, state='succeeded')
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'pass')

    # 6. A re-queued job carrying a historical started_at is NOT
    #    classified as a never-started stalled job (documented boundary).
    def test_cron_queue_health_requeued_job_with_history_not_stalled(self):
        self._make_queued_job(
            self.store, age_minutes=200, state='queued',
            started_at=fields.Datetime.now() - timedelta(minutes=180),
        )
        check = self.ReadinessCheck._check_cron_queue_health(self.store)
        self.assertEqual(check['result'], 'pass')

    # 7. A connector administrator WITHOUT ERP-manager permissions can
    #    run the readiness cron check, because the cron read uses the one
    #    narrow sudo elevation. Proven load-bearing: the same user's
    #    direct (non-elevated) ir.cron read is denied.
    def test_cron_queue_health_connector_admin_runs_via_sudo_elevation(self):
        cron = self.env.ref(DRAIN_CRON_XMLID)
        with self.assertRaises(AccessError):
            cron.with_user(self.user_admin).read(['active'])
        check = self.ReadinessCheck.with_user(
            self.user_admin
        )._check_cron_queue_health(self.store.with_user(self.user_admin))
        self.assertEqual(check['result'], 'pass')

    # ==================================================================
    # D-R1-2 -- mapped_location
    # ==================================================================

    # 8. Inventory disabled -> not-applicable pass (both the no-settings
    #    case and an explicit inventory_domain_enabled=False settings).
    def test_mapped_location_inventory_disabled_passes_not_applicable(self):
        check_no_settings = self.ReadinessCheck._check_mapped_location(
            self.store
        )
        self.assertEqual(check_no_settings['result'], 'pass')
        self.assertIn('not enabled', check_no_settings['reason'].lower())

        self.Settings.create({
            'store_id': self.store.id, 'inventory_domain_enabled': False,
        })
        self.store.invalidate_recordset()
        check_flag_false = self.ReadinessCheck._check_mapped_location(
            self.store
        )
        self.assertEqual(check_flag_false['result'], 'pass')

    # 9. Inventory enabled but no inventory override -> not_proven
    #    (fail-closed).
    def test_mapped_location_inventory_enabled_without_override_not_proven(self):
        self.Settings.create({
            'store_id': self.store.id, 'inventory_domain_enabled': True,
        })
        check = self.ReadinessCheck._check_mapped_location(self.store)
        self.assertEqual(check['result'], 'not_proven')

    # ==================================================================
    # D-R1-3 -- webhook_hmac
    # ==================================================================

    # 10. Webhook intake absent -> not-applicable pass with the EXACT
    #     packet reason string.
    def test_webhook_hmac_not_applicable_pass_exact_reason(self):
        check = self.ReadinessCheck._check_webhook_hmac(self.store)
        self.assertEqual(check['result'], 'pass')
        self.assertEqual(check['reason'], WEBHOOK_HMAC_NA_REASON)

    # ==================================================================
    # D-R1-5 -- healthy API state write
    # ==================================================================

    # 11. Successful non-fall-forward connection sets api_health_state
    #     'normal' (real test-connection path, not a force-write).
    def test_non_fallforward_success_sets_api_health_normal(self):
        store = self._make_store('normal-health')
        self._set_token(store)
        self._run_test_connection(
            store,
            FakeResponse(200, json_body=_success_body(domain=store.shop_domain)),
        )
        store.invalidate_recordset()
        self.assertEqual(store.last_test_connection_result, 'pass')
        self.assertEqual(store.api_health_state, 'normal')

    # 12. Fall-forward connection still sets api_health_state 'degraded'
    #     (the D-R1-5 change never touches this path).
    def test_fallforward_now_fails_the_probe_instead_of_degrading(self):
        """Inverted by the 2026-07-26 API-version ruling.

        Formerly `test_fallforward_success_still_sets_api_health_degraded`,
        which asserted `last_test_connection_result == 'pass'` with a
        `degraded` health state. "Verified, but against a schema we did not
        check" is exactly the soft disposition that ruling removes: a store
        served on another API version is not a connection this connector can
        vouch for, so the probe FAILS and the store is not marked verified.
        """
        store = self._make_store('degraded-health')
        self._set_token(store)
        self._run_test_connection(
            store,
            FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain),
                headers={'X-Shopify-API-Version': '2026-10'},
            ),
        )
        store.invalidate_recordset()
        self.assertEqual(store.last_test_connection_result, 'fail')
        self.assertTrue(store.last_test_connection_reason)

    # 12b. Recovery regression: a store that fell forward to `degraded`
    #      (with a populated reason) returns to `normal` on a subsequent
    #      non-fall-forward success, and the stale reason is cleared --
    #      both states reached through real test-connection behavior, no
    #      force-writes.
    def test_a_failed_probe_recovers_to_normal_and_clears_reason(self):
        """Recovery regression, re-anchored on the post-ruling behaviour.

        The `degraded` state is no longer reachable through a fall-forward
        success (that path now fails closed), so the regression this test
        exists for -- a stale `api_health_reason` surviving a later success --
        is reproduced by reaching a failed probe first and then succeeding.
        Both states are still reached through real test-connection behaviour,
        with no force-writes.
        """
        store = self._make_store('recovery')
        self._set_token(store)
        # 1) a version mismatch -> failed probe with a non-empty reason.
        self._run_test_connection(
            store,
            FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain),
                headers={'X-Shopify-API-Version': '2026-10'},
            ),
        )
        store.invalidate_recordset()
        self.assertEqual(store.last_test_connection_result, 'fail')
        self.assertTrue(store.last_test_connection_reason)
        # 2) subsequent correctly-versioned success -> normal, reason cleared.
        self._run_test_connection(
            store,
            FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain)
            ),
        )
        store.invalidate_recordset()
        self.assertEqual(store.api_health_state, 'normal')
        self.assertFalse(store.api_health_reason)

    # ==================================================================
    # D-R1-4 -- eligible Lite store reaches connected (real behavior)
    # ==================================================================

    # 13. A fully configured Lite store aggregates readiness `pass`.
    def test_eligible_lite_store_aggregates_pass(self):
        store = self._provision_ready_lite_store('lite-pass')
        result = self.ReadinessCheck.run_for_store(store)
        self.assertEqual(result['overall_result'], 'pass')
        # Every essential check individually passed -- prove none is a
        # residual not_proven placeholder.
        for check in result['checks']:
            self.assertEqual(
                check['result'], 'pass',
                'check %s was %s: %s' % (
                    check['code'], check['result'], check['reason'],
                ),
            )

    # 14. The same eligible Lite store reaches `connected` through
    #     action_activate(), on real evidence (no state force-write).
    def test_eligible_lite_store_reaches_connected(self):
        store = self._provision_ready_lite_store('lite-connect')
        self.ReadinessCheck.run_for_store(store)
        store.with_user(self.user_admin).action_activate()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')

    # 15. A genuine essential failure (missing required scope) still
    #     prevents activation -- fail-closed behavior preserved.
    def test_genuine_essential_failure_still_blocks_activation(self):
        scopes = list(self.ReadinessCheck.REQUIRED_MVP_SCOPES)[:-1]
        store = self._provision_ready_lite_store('lite-fail', scopes=scopes)
        result = self.ReadinessCheck.run_for_store(store)
        self.assertEqual(result['overall_result'], 'fail')
        with self.assertRaises(UserError):
            store.with_user(self.user_admin).action_activate()
        store.invalidate_recordset()
        self.assertNotEqual(store.state, 'connected')

    # ==================================================================
    # 16. Source-level guards
    # ==================================================================

    def _models_dir(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )

    def _readiness_source_tree(self):
        path = os.path.join(
            self._models_dir(), 'shopify_connector_readiness_check.py'
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            return ast.parse(source_file.read(), filename=path)

    def test_source_level_checks_add_no_shopify_call_or_credential_read(self):
        """The three edited check methods add no Shopify API call, no
        credential read, and no elevation of their own -- the only new
        sudo is the named `_drain_cron_active_state` helper (D-R1-1)."""
        tree = self._readiness_source_tree()
        edited_checks = {
            '_check_webhook_hmac', '_check_mapped_location',
            '_check_cron_queue_health',
        }
        forbidden_attrs = {'sudo', 'execute', 'write', 'create', 'unlink'}
        forbidden_names = {'access_token', 'api.client', 'api_client'}
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.FunctionDef)
                and node.name in edited_checks
            ):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr in forbidden_attrs
                ):
                    self.fail(
                        '%s must not call .%s' % (
                            node.name, inner.func.attr,
                        )
                    )
                if isinstance(inner, ast.Constant) and isinstance(
                    inner.value, str
                ):
                    lowered = inner.value.lower()
                    for banned in forbidden_names:
                        self.assertNotIn(banned, lowered)

    def test_source_level_sec1_sudo_inventory_in_readiness(self):
        """SEC-1 adds protected job create/final-write elevation to
        run_for_store; CORE-R1 retains the one cron-read elevation; S1 adds
        the system-parameter read (2026-07-27).

        The `web.base.url` read needs elevation for the same reason the cron
        read does: system parameters are `base.group_system` in Odoo 19 and
        readiness runs as the invoking connector administrator, who is not
        necessarily an Odoo system administrator. Without it the check raised
        AccessError and failed the whole run -- reachable in production
        through `action_reconnect` before the guided setup existed.
        """
        self.assertEqual(
            core_sudo_inventory_for_file(
                'shopify_connector_readiness_check.py'
            ),
            (
                (
                    'shopify_connector_readiness_check.py',
                    '_drain_cron_active_state', 'cron', 1,
                    'Read cron configuration.',
                ),
                (
                    'shopify_connector_readiness_check.py',
                    '_web_base_url', "self.env['ir.config_parameter']", 1,
                    'Read public base-URL configuration.',
                ),
                (
                    'shopify_connector_readiness_check.py',
                    'run_for_store', 'Job', 1,
                    'Readiness audit job lifecycle.',
                ),
                (
                    'shopify_connector_readiness_check.py',
                    'run_for_store', 'job', 1,
                    'Readiness audit job lifecycle.',
                ),
            ),
        )

    def test_source_level_store_health_and_sec1_sudo_inventory(self):
        """CORE-R1's health write remains singular while SEC-1 adds only
        the nine named store-side protected job writer elevations, plus the
        two SEC-3 (#197) ownership seams."""
        path = os.path.join(
            self._models_dir(), 'shopify_connector_store.py'
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
        # 1 -> 2 (TD-014, authorised deliberately). CORE-R1's write on a
        # verified probe is still there and still singular. The second is
        # the rate-backpressure RELEASE in
        # `_apply_throttle_backpressure`: a store deferred for exhausted
        # Shopify head-room has to be able to return to `normal` when the
        # bucket refills, or PERF-1's lever becomes a one-way trip and the
        # first deferral is permanent.
        #
        # The two writers do not overlap. CORE-R1's records a verified
        # connection probe; this one only ever releases a deferral IT
        # made, gated on `api_health_state == 'throttled'`, so it can
        # neither manufacture a verification nor clear a `degraded` state
        # set by anything else.
        self.assertEqual(content.count("'api_health_state': 'normal'"), 2)
        self.assertEqual(
            content.count("'api_health_state': 'throttled'"), 1,
            'Exactly one production writer may defer a store for rate '
            'pressure (TD-014).',
        )
        # The 2026-07-26 API-version ruling removed the fall-forward branch
        # that wrote `degraded` on an otherwise-successful probe: a served
        # version that differs from the connector constant now fails closed in
        # `_normalize_response` and never reaches the success path. The
        # `degraded` VALUE remains in the selection and is still reachable
        # through other health transitions; what no longer exists is a write
        # of it next to a recorded verification.
        self.assertNotIn("'api_health_state': 'degraded'", content)
        self.assertEqual(
            core_sudo_inventory_for_file('shopify_connector_store.py'),
            (
                ('shopify_connector_store.py', '_apply_probe_failure',
                 'job', 1, 'Probe failure transition.'),
                # TD-014 (PERF-1 / D-PERF1-4): the rate-head-room lever.
                # Every one of these writes only this store's own
                # `api_throttle_*` numerics and the health state derived
                # from them. `api_health_state`, `api_health_reason` and
                # the four numerics are readonly protected fields, so the
                # service that maintains them cannot write them
                # unelevated. No credential, no request payload and no
                # cross-store disclosure: the recovery sweep searches only
                # stores the cron user can already see.
                ('shopify_connector_store.py',
                 '_apply_throttle_backpressure', 'self', 1,
                 'Rate backpressure health write.'),
                ('shopify_connector_store.py',
                 '_apply_throttle_backpressure', 'self', 2,
                 'Rate backpressure health write.'),
                ('shopify_connector_store.py', '_audit_probe_superseded',
                 'job', 1, 'Probe supersession audit.'),
                # SEC-3 (#197) ownership seams. Recorded here as well as in
                # test_credential_service, because this assertion is the
                # store-file-specific copy of the same trust-surface contract.
                ('shopify_connector_store.py', '_backfill_company',
                 "self.env['res.company']", 1,
                 'SEC-3 ownership backfill probe.'),
                ('shopify_connector_store.py', 'action_assign_company',
                 'self', 1, 'SEC-3 administrative ownership remediation.'),
                # Batch 2 correction (F7). The merchant-facing "scheduled
                # import" state is a lie unless it consults the cron that
                # would actually perform it, and `ir.cron` is Administrator-
                # only by ACL -- an Operator reading their own store's page is
                # not one. The elevation is the narrowest available: `env.ref`
                # resolves a module-owned external id BEFORE anything
                # elevates, so `sudo()` is never used to DISCOVER a record,
                # only to read `active` on the one this connector installed.
                # One Boolean read, no write, and False for anything that is
                # not a live `ir.cron`.
                ('shopify_connector_store.py',
                 '_connector_scheduler_is_active', 'cron', 1,
                 'Truthful scheduled-state projection: reads `active` on the '
                 'module-owned cron already resolved by external id.'),
                ('shopify_connector_store.py',
                 '_create_lifecycle_audit_job', 'Job', 1,
                 'Lifecycle audit carrier.'),
                ('shopify_connector_store.py',
                 '_create_lifecycle_audit_job', 'job', 1,
                 'Lifecycle audit carrier.'),
                ('shopify_connector_store.py', '_record_throttle_status',
                 'self', 1, 'Rate head-room observation write.'),
                ('shopify_connector_store.py', '_recover_throttled_stores',
                 'self', 1, 'Rate deferral recovery sweep.'),
                ('shopify_connector_store.py', '_run_connection_probe',
                 'Job', 1, 'Probe audit job lifecycle.'),
                # Wave 5. The probe obtains/refreshes a client-credentials
                # token before it creates its audit job, so an authentication
                # failure at that point has no job to be recorded against. This
                # second `Job` elevation creates one and hands it to the
                # unchanged `_apply_probe_failure`, so the failure is audited
                # exactly like every other probe failure rather than escaping
                # as an unhandled error. Same store, same job shape, no new
                # trust surface.
                ('shopify_connector_store.py', '_run_connection_probe',
                 'Job', 2, 'Probe audit job lifecycle.'),
                ('shopify_connector_store.py', '_run_connection_probe',
                 'Job', 3, 'Probe audit job lifecycle.'),
                ('shopify_connector_store.py', '_run_connection_probe',
                 'job', 1, 'Probe audit job lifecycle.'),
                ('shopify_connector_store.py', '_run_connection_probe',
                 'job', 2, 'Probe audit job lifecycle.'),
                ('shopify_connector_store.py',
                 '_sweep_quiescing_business_jobs', 'job', 1,
                 'Disconnect job sweep.'),
                ('shopify_connector_store.py', 'action_force_disconnect',
                 'job', 1, 'Forced-disconnect audit.'),
            ),
        )
