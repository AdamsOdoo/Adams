import ast
import json
import os
import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


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
class TestReadinessCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Readiness Check Test Store',
            'shop_domain': 'readiness-check-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.ReadinessCheck = cls.env['shopify.connector.readiness.check']

    def _logs_for(self, job):
        return self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)], order='id asc',
        )

    # ------------------------------------------------------------------
    # 1. TD-001 regression
    # ------------------------------------------------------------------

    def test_td001_repeated_readiness_job_does_not_collide(self):
        result_1 = self.ReadinessCheck.run_for_store(self.store)
        result_2 = self.ReadinessCheck.run_for_store(self.store)
        self.assertEqual(result_1['job'].state, 'succeeded')
        self.assertEqual(result_2['job'].state, 'succeeded')
        jobs = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])
        self.assertEqual(len(jobs), 2)
        self.assertEqual(len(set(jobs.mapped('payload_hash'))), 2)
        self.assertEqual(len(set(jobs.mapped('idempotency_key'))), 2)

    # ------------------------------------------------------------------
    # 2. core_test_connection repeat-run behavior unchanged (focused
    # assertion against the shared job substrate this fix touches --
    # shopify_connector_job.py/shopify_connector_store.py are untouched
    # by this task, so the existing action_test_connection UUID4-nonce
    # behavior is exercised exhaustively by test_test_connection.py; this
    # confirms the underlying idempotency-key substrate this readiness
    # fix relies on still behaves identically for the sibling job type).
    # ------------------------------------------------------------------

    def test_core_test_connection_repeat_run_still_does_not_collide(self):
        Job = self.env['shopify.connector.job']
        job_1 = Job.create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
        })
        job_2 = Job.create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
        })
        self.assertNotEqual(job_1.idempotency_key, job_2.idempotency_key)

    # ------------------------------------------------------------------
    # 3-6. Aggregation semantics (direct unit tests of _aggregate)
    # ------------------------------------------------------------------

    def _check(self, tier, result, code='x'):
        return self.ReadinessCheck._check_result(code, tier, result, 'reason')

    def test_aggregate_essential_failure_yields_overall_fail(self):
        checks = [
            self._check('essential', 'pass', 'a'),
            self._check('essential', 'fail', 'b'),
            self._check('warning', 'pass', 'c'),
        ]
        self.assertEqual(self.ReadinessCheck._aggregate(checks), 'fail')

    def test_aggregate_warning_only_failure_does_not_yield_fail(self):
        checks = [
            self._check('essential', 'pass', 'a'),
            self._check('essential', 'pass', 'b'),
            self._check('warning', 'fail', 'c'),
        ]
        self.assertEqual(self.ReadinessCheck._aggregate(checks), 'warning')

    def test_aggregate_unknown_essential_yields_overall_fail(self):
        checks = [
            self._check('essential', 'pass', 'a'),
            self._check('essential', 'not_proven', 'b'),
        ]
        self.assertEqual(self.ReadinessCheck._aggregate(checks), 'fail')

    def test_aggregate_all_pass_yields_overall_pass(self):
        checks = [
            self._check('essential', 'pass', 'a'),
            self._check('essential', 'pass', 'b'),
            self._check('warning', 'pass', 'c'),
        ]
        self.assertEqual(self.ReadinessCheck._aggregate(checks), 'pass')

    # ------------------------------------------------------------------
    # 7. No VAL-B2 evidence -> credential/test-connection check never passes
    # ------------------------------------------------------------------

    def test_credential_check_unproven_without_val_b2_evidence(self):
        self.assertFalse(self.store.last_test_connection_result)
        check = self.ReadinessCheck._check_credential_test_connection(
            self.store
        )
        self.assertEqual(check['result'], 'not_proven')
        self.assertNotEqual(check['result'], 'pass')

    def test_credential_check_fails_on_stored_failure(self):
        self.store.write({'last_test_connection_result': 'fail'})
        check = self.ReadinessCheck._check_credential_test_connection(
            self.store
        )
        self.assertEqual(check['result'], 'fail')

    def test_credential_check_passes_only_on_stored_pass(self):
        self.store.write({'last_test_connection_result': 'pass'})
        check = self.ReadinessCheck._check_credential_test_connection(
            self.store
        )
        self.assertEqual(check['result'], 'pass')

    # ------------------------------------------------------------------
    # 8. Per-check JSON in job.log.payload_snapshot
    # ------------------------------------------------------------------

    def test_payload_snapshot_contains_per_check_json(self):
        result = self.ReadinessCheck.run_for_store(self.store)
        job = result['job']
        logs = self._logs_for(job)
        verification_logs = logs.filtered(
            lambda l: l.event_type == 'verification_read'
        )
        self.assertEqual(len(verification_logs), 1)
        snapshot = json.loads(verification_logs.payload_snapshot)
        self.assertEqual(len(snapshot), len(result['checks']))
        for entry in snapshot:
            self.assertIn('code', entry)
            self.assertIn('tier', entry)
            self.assertIn('result', entry)
            self.assertIn('reason', entry)

    # ------------------------------------------------------------------
    # 9. Summary mirror writes to store readiness fields
    # ------------------------------------------------------------------

    def test_summary_mirrors_onto_store_readiness_fields(self):
        self.assertFalse(self.store.last_readiness_result)
        result = self.ReadinessCheck.run_for_store(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.last_readiness_result, result['overall_result']
        )
        self.assertTrue(self.store.last_readiness_at)

    def test_fresh_store_never_passes_readiness(self):
        # A fresh store has no stored VAL-B2 evidence and several
        # essential checks are still pending core-only slots (webhook
        # HMAC, mapped Location, cron/queue) -- fail-closed aggregation
        # must never infer an overall pass from that absence.
        result = self.ReadinessCheck.run_for_store(self.store)
        self.assertEqual(result['overall_result'], 'fail')

    # ------------------------------------------------------------------
    # 10. Domain-extension seam: a check can be registered from outside
    # shopify_connector_core without modifying core files.
    # ------------------------------------------------------------------

    def test_extension_seam_registers_check_without_modifying_core(self):
        ReadinessCheckModel = self.env.registry[
            'shopify.connector.readiness.check'
        ]
        original_get_checks = ReadinessCheckModel._get_checks

        def _extended_get_checks(self, store):
            # Exactly the pattern a domain module's `_inherit` override
            # would use: call super(), then append -- never mutate.
            checks = original_get_checks(self, store)
            checks.append(self._check_result(
                'domain_extension_probe', self.WARNING, self.RESULT_PASS,
                'Injected by a domain-extension seam test.',
            ))
            return checks

        with patch.object(
            ReadinessCheckModel, '_get_checks', _extended_get_checks,
        ):
            checks = self.ReadinessCheck._get_checks(self.store)
        codes = [check['code'] for check in checks]
        self.assertIn('domain_extension_probe', codes)
        # The core-owned checks are still present, unmutated.
        self.assertIn('credential_test_connection', codes)

    # ------------------------------------------------------------------
    # 11. Read-only guarantee
    # ------------------------------------------------------------------

    def test_readiness_check_never_calls_shopify_api_client(self):
        Client = self.env['shopify.connector.api.client']

        def _fail_if_called(self, store, query, variables=None):
            raise AssertionError(
                'Readiness check must never call the Shopify API client.'
            )

        with patch.object(type(Client), 'execute', _fail_if_called):
            result = self.ReadinessCheck.run_for_store(self.store)
        self.assertEqual(result['job'].state, 'succeeded')

    def test_readiness_check_only_writes_its_own_mirror_fields(self):
        before = self.store.read()[0]
        self.ReadinessCheck.run_for_store(self.store)
        self.store.invalidate_recordset()
        after = self.store.read()[0]
        ignored_write_tracking_fields = (
            '__last_update', 'write_date', 'write_uid',
        )
        changed = {
            key for key in before
            if key not in ignored_write_tracking_fields
            and before[key] != after[key]
        }
        self.assertEqual(
            changed, {'last_readiness_result', 'last_readiness_at'}
        )

    def test_source_level_no_check_method_mutates_state(self):
        """AST guard: no `_check_*` method may call write/create/unlink/execute.

        Mirrors the existing `test_source_level_two_sudo_sites_total`
        convention (test_job_log_system_append.py) -- a structural
        guarantee, not just a behavioral sample, that every registered
        check is provably read-only.
        """
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        path = os.path.join(models_dir, 'shopify_connector_readiness_check.py')
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)
        mutating_attrs = {'write', 'create', 'unlink', 'execute', 'sudo'}
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith('_check_')):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr in mutating_attrs
                ):
                    offenders.append((node.name, inner.func.attr))
        self.assertEqual(offenders, [])

    # ------------------------------------------------------------------
    # 12. Redaction / no secret leakage
    # ------------------------------------------------------------------

    def test_no_secret_leakage_in_job_or_log(self):
        self.store.write({
            'last_test_connection_result': 'fail',
            'last_test_connection_reason': (
                'token %s appeared in a stored reason' % DUMMY_TOKEN
            ),
        })
        result = self.ReadinessCheck.run_for_store(self.store)
        job = result['job']
        logs = self._logs_for(job)
        for recordset in (job, logs):
            fields_info = recordset.fields_get()
            for field_name, info in fields_info.items():
                if info['type'] not in ('char', 'text'):
                    continue
                for rec in recordset:
                    value = rec[field_name]
                    if value:
                        self.assertNotIn(DUMMY_TOKEN, value)

    # ------------------------------------------------------------------
    # 13. Required scopes: must validate the accepted MVP scope set
    # (REQUIRED_MVP_SCOPES), not merely a non-empty list.
    # ------------------------------------------------------------------

    def _scopes_json(self, scopes):
        return json.dumps(list(scopes))

    def test_required_scopes_all_present_passes(self):
        self.store.write({
            'granted_scopes': self._scopes_json(
                self.ReadinessCheck.REQUIRED_MVP_SCOPES
            ),
        })
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'pass')

    def test_required_scopes_missing_one_fails_and_identifies_it(self):
        scopes = list(self.ReadinessCheck.REQUIRED_MVP_SCOPES)
        missing_scope = scopes.pop()
        self.store.write({'granted_scopes': self._scopes_json(scopes)})
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'fail')
        self.assertNotEqual(check['result'], 'pass')
        self.assertIn(missing_scope, check['reason'])

    def test_required_scopes_extra_scope_still_passes(self):
        scopes = list(self.ReadinessCheck.REQUIRED_MVP_SCOPES) + [
            'read_draft_orders',
        ]
        self.store.write({'granted_scopes': self._scopes_json(scopes)})
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'pass')

    def test_required_scopes_single_scope_is_not_enough(self):
        # A non-empty snapshot missing most required scopes must not
        # pass -- this is the exact defect ChatGPT review found: any
        # non-empty list used to pass.
        self.store.write({
            'granted_scopes': json.dumps(['read_products']),
        })
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'fail')

    def test_required_scopes_malformed_json_not_proven(self):
        self.store.write({'granted_scopes': 'not-valid-json'})
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'not_proven')

    def test_required_scopes_empty_list_not_proven(self):
        self.store.write({'granted_scopes': json.dumps([])})
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'not_proven')

    def test_required_scopes_absent_not_proven(self):
        self.assertFalse(self.store.granted_scopes)
        check = self.ReadinessCheck._check_required_scopes(self.store)
        self.assertEqual(check['result'], 'not_proven')

    def test_required_scopes_use_merchant_managed_fulfillment_orders(self):
        # TD-002 / D-014-2: the FulfillmentOrder-based mutation flow requires
        # read_merchant_managed_fulfillment_orders; the legacy read_fulfillments
        # scope (FulfillmentService apps) is no longer in the required set.
        self.assertIn(
            'read_merchant_managed_fulfillment_orders',
            self.ReadinessCheck.REQUIRED_MVP_SCOPES,
        )
        self.assertNotIn(
            'read_fulfillments', self.ReadinessCheck.REQUIRED_MVP_SCOPES,
        )

    # ------------------------------------------------------------------
    # 14. Domain flag enablement: must pass only when at least one
    # accepted domain flag is True, not merely because a settings record
    # exists.
    # ------------------------------------------------------------------

    def _create_settings(self, **flags):
        return self.env['shopify.connector.store.settings'].create({
            'store_id': self.store.id,
            **flags,
        })

    def test_domain_flag_no_settings_record_not_proven(self):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', self.store.id)]
        )
        self.assertFalse(settings)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'not_proven')

    def test_domain_flag_settings_with_all_flags_false_does_not_pass(self):
        # This is the exact defect ChatGPT review found: a settings
        # record's mere existence used to pass, even with every domain
        # flag False (i.e., no sync domain would actually run).
        self._create_settings()
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'fail')
        self.assertNotEqual(check['result'], 'pass')
        self.assertIn('No sync domain is enabled', check['reason'])

    def test_domain_flag_notification_default_alone_does_not_pass(self):
        # notification_default_enabled is not one of the four accepted
        # sync-domain flags and must never cause a pass by itself.
        self._create_settings(notification_default_enabled=True)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertNotEqual(check['result'], 'pass')

    def test_domain_flag_product_domain_enabled_passes(self):
        self._create_settings(product_domain_enabled=True)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'pass')

    def test_domain_flag_sale_domain_enabled_passes(self):
        self._create_settings(sale_domain_enabled=True)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'pass')

    def test_domain_flag_inventory_domain_enabled_passes(self):
        self._create_settings(inventory_domain_enabled=True)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'pass')

    def test_domain_flag_fulfillment_domain_enabled_passes(self):
        self._create_settings(fulfillment_domain_enabled=True)
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['result'], 'pass')

    # ------------------------------------------------------------------
    # 15. Correction B (independent review, Defects #2/#3): tier and the
    # extensible flag-registration seam.
    # ------------------------------------------------------------------

    def test_domain_flag_check_is_warning_tier_not_essential(self):
        """The exact tier correction: a zero-domain result must never be
        able to fail the essential aggregate by itself."""
        self._create_settings()
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['tier'], self.ReadinessCheck.WARNING)
        self.assertEqual(check['result'], 'fail')

    def test_no_settings_record_is_also_warning_tier(self):
        check = self.ReadinessCheck._check_domain_flag_enablement(
            self.store
        )
        self.assertEqual(check['tier'], self.ReadinessCheck.WARNING)
        self.assertEqual(check['result'], 'not_proven')

    def test_accepted_domain_flags_includes_the_core_owned_tuple(self):
        """The extension seam's base guarantee: every core-owned flag is
        always present. Asserted as a subset, not an exact match -- whatever
        other connector domain modules happen to be installed alongside
        core in this test environment may legitimately register more, the
        same way `shopify_connector_product_export` does."""
        result = tuple(self.ReadinessCheck._accepted_domain_flags())
        for flag in self.ReadinessCheck.ACCEPTED_DOMAIN_FLAGS:
            self.assertIn(flag, result)

    def test_an_unrecognized_registered_flag_fails_closed_rather_than_raising(
        self,
    ):
        """A domain module could register a flag name that is not actually
        a field on `shopify.connector.store.settings` -- a stale or
        misconfigured registration. That must fail closed to "not
        enabled", never raise and never be silently treated as enabled."""
        self._create_settings()
        with patch.object(
            type(self.ReadinessCheck), '_accepted_domain_flags',
            lambda self: ('not_a_real_settings_field',),
        ):
            check = self.ReadinessCheck._check_domain_flag_enablement(
                self.store
            )
        self.assertEqual(check['result'], 'fail')

    def test_governed_scope_catalog_includes_the_core_owned_reasons(self):
        """The step-4 display-list extension seam's base guarantee: every
        core-owned scope is always present, with a reason. Asserted as a
        subset for the same reason as the domain-flags test above."""
        catalog = self.ReadinessCheck._governed_scope_catalog()
        scopes = {entry['scope'] for entry in catalog}
        for scope in self.ReadinessCheck.REQUIRED_MVP_SCOPES:
            self.assertIn(scope, scopes)
        for entry in catalog:
            self.assertTrue(entry['reason'])
