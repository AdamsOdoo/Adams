import uuid
from unittest.mock import Mock, patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
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
class TestMutationReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 reconciliation test',
            'shop_domain': 'layer2-reconcile-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.admin = cls.env['res.users'].create({
            'name': 'Layer 2 reconciliation administrator',
            'login': 'layer2_reconciliation_admin_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.'
                    'group_shopify_connector_admin'
                ).id,
            ])],
        })

    def _fixture(self, direct_outcome=True, create_reconciliation=True):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
        })
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        if direct_outcome:
            attempt._record_direct_outcome(
                'uncertain', evidence={'request_id': 'synthetic-direct'},
            )
        reconciliation = self.Job
        if create_reconciliation:
            reconciliation = self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'reconciliation',
                'job_type': 'mutation_dispatch_selftest_reconcile',
                'state': 'running',
                'payload_hash': 'reconcile:%s' % token,
                'mutation_attempt_id': attempt.id,
                'expected_connection_generation':
                    attempt.expected_connection_generation,
            })
        return job, attempt, reconciliation

    def test_resolution_preserves_direct_and_appends_read_evidence(self):
        job, attempt, reconciliation = self._fixture()
        direct = attempt.remote_evidence_refs['direct']
        attempt._record_reconciliation_result(
            'applied', evidence={'read': 'synthetic'},
        )
        self.assertEqual(attempt.effective_disposition(), 'applied')
        self.assertEqual(job.state, 'running')
        self.assertEqual(attempt.resolution_source, 'reconciliation_read')
        self.assertEqual(attempt.remote_evidence_refs['direct'], direct)
        self.assertEqual(len(
            attempt.remote_evidence_refs['reconciliation']
        ), 1)
        self.env['shopify.connector.job.dispatch']._complete_reconciliation_job(
            reconciliation, 'Synthetic resolved read completed.'
        )
        self.assertEqual(reconciliation.state, 'succeeded')

    def test_not_applied_resolution_never_requeues_same_job(self):
        job, attempt, _reconciliation = self._fixture()
        attempt._record_reconciliation_result('not_applied', {})
        self.assertEqual(attempt.effective_disposition(), 'not_applied')
        self.assertEqual(job.state, 'running')

    def test_valid_reconciliation_consequence_is_atomic_and_terminal(self):
        job, attempt, reconciliation = self._fixture()
        self.env[
            'shopify.connector.job.dispatch'
        ]._handle_mutation_dispatch_selftest_reconcile(reconciliation)
        self.assertEqual(attempt.effective_disposition(), 'applied')
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(reconciliation.state, 'succeeded')

    def test_inconclusive_cap_is_per_attempt_and_fail_closed(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        direct = attempt.remote_evidence_refs['direct']
        strategy['reconcile'] = lambda _attempt, _reconciliation_job: {
            'verdict': 'inconclusive',
            'observed_store_identity': attempt.expected_store_identity,
            'action': 'reconcile',
            'error_class': 'shopify_temporary_server_network',
            'manual_review_subreason': False,
            'message': 'Synthetic read remains inconclusive.',
            'evidence': {'read': 'synthetic'},
        }
        for count in range(1, 4):
            if reconciliation.state != 'running':
                reconciliation.sudo().write({'state': 'running'})
            with patch.object(
                type(Dispatch), '_get_reconciliation_strategies',
                return_value={attempt.mutation_domain: strategy},
            ):
                Dispatch._handle_mutation_dispatch_selftest_reconcile(
                    reconciliation
                )
            self.assertEqual(
                attempt.inconclusive_reconciliation_count, count,
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')
        self.assertEqual(reconciliation.state, 'succeeded')
        self.assertEqual(attempt.remote_evidence_refs['direct'], direct)
        self.assertEqual(len(
            attempt.remote_evidence_refs['reconciliation']
        ), 3)
        self.assertFalse(attempt.resolution_disposition)

    def test_exact_reconciliation_link_is_required(self):
        with self.assertRaises(ValidationError):
            self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'reconciliation',
                'job_type': 'mutation_dispatch_selftest_reconcile',
                'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
            })

    def test_store_identity_mismatch_blocks_original_without_verdict(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        strategy['reconcile'] = lambda _attempt, _reconciliation_job: {
            'verdict': 'applied',
            'observed_store_identity': 'different-shop.myshopify.com',
            'action': 'succeed',
            'error_class': False,
            'manual_review_subreason': False,
            'message': 'Synthetic mismatched identity.',
            'evidence': {'read': 'synthetic'},
        }
        with patch.object(
            type(Dispatch), '_get_reconciliation_strategies',
            return_value={attempt.mutation_domain: strategy},
        ):
            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                reconciliation
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.error_class, 'store_identity_mismatch')
        self.assertEqual(reconciliation.state, 'succeeded')
        self.assertFalse(attempt.resolution_disposition)

    def test_missing_strategy_routes_original_job_not_read_job(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        with patch.object(
            type(Dispatch), '_get_reconciliation_strategies',
            return_value={},
        ):
            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                reconciliation
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.error_class, 'no_reconciliation_strategy')
        self.assertEqual(reconciliation.state, 'succeeded')
        self.assertFalse(attempt.resolution_disposition)

    def test_callback_failure_rolls_back_job_and_created_child(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        marker = 'callback-child:%s' % uuid.uuid4().hex

        def failing_callback(*_args, **_kwargs):
            self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'core_dispatch_selftest',
                'state': 'queued',
                'payload_hash': marker,
            })
            raise RuntimeError('synthetic callback rollback')

        strategy['apply_consequence'] = failing_callback
        consequence = {
            'observed_outcome': 'uncertain',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': 'Synthetic applied verdict.',
            'evidence': {},
        }
        log_domain = [('job_id', '=', job.id)]
        log_count = self.env[
            'shopify.connector.job.log'
        ].search_count(log_domain)
        with self.assertRaisesRegex(
            RuntimeError, 'synthetic callback rollback',
        ):
            with self.env.cr.savepoint():
                attempt._record_reconciliation_result(
                    'applied', {'read': 'synthetic'},
                )
                Dispatch._apply_validated_consequence(
                    job, attempt, 'reconciliation', consequence, strategy,
                    reconciliation_job=reconciliation,
                )
        job.invalidate_recordset()
        attempt.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(attempt.resolution_disposition)
        self.assertFalse(attempt.resolved_at)
        self.assertEqual(
            self.env['shopify.connector.job.log'].search_count(log_domain),
            log_count,
        )
        self.assertFalse(self.Job.search_count([
            ('payload_hash', '=', marker),
        ]))

    def test_historic_reconciliation_keeps_attempt_evidence_link(self):
        _job, attempt, reconciliation = self._fixture()
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        attempt._record_inconclusive_reconciliation({
            'read_ref': 'historic-safe-read',
        })
        attempt.with_user(self.admin).action_resolve_mutation_attempt(
            'applied', 'Historic conversion was externally verified.',
        )
        evidence = attempt.remote_evidence_refs
        original_job_type = reconciliation.original_job_type
        log_domain = [('job_id', '=', reconciliation.id)]
        log_count = self.env[
            'shopify.connector.job.log'
        ].search_count(log_domain)
        reconciliation._reassign_to_historic_job_type()
        self.assertEqual(reconciliation.job_type, 'historic_domain_job')
        self.assertEqual(
            reconciliation.original_job_type, original_job_type,
        )
        self.assertEqual(reconciliation.mutation_attempt_id, attempt)
        self.assertTrue(reconciliation.exists())
        self.assertTrue(attempt.exists())
        self.assertEqual(attempt.remote_evidence_refs, evidence)
        self.assertGreaterEqual(
            self.env['shopify.connector.job.log'].search_count(log_domain),
            log_count,
        )

    def test_recovered_pending_attempt_reconciles_end_to_end(self):
        Dispatch = self.env['shopify.connector.job.dispatch']
        for verdict, action, expected_state, disposition in (
            ('applied', 'succeed', 'succeeded', 'applied'),
            ('not_applied', 'cancel', 'cancelled', 'not_applied'),
        ):
            job, attempt, _unused = self._fixture(
                direct_outcome=False, create_reconciliation=False,
            )
            transport = Mock(side_effect=AssertionError(
                'mutation transport must not replay during recovery'
            ))
            strategy = dict(Dispatch._get_reconciliation_strategies()[
                attempt.mutation_domain
            ])
            strategy['transport'] = transport

            def recovered_result(
                _attempt, _reconciliation_job,
                verdict=verdict, action=action,
            ):
                return {
                    'verdict': verdict,
                    'observed_store_identity': self.store.shop_domain,
                    'action': action,
                    'error_class': False,
                    'manual_review_subreason': False,
                    'message': 'Synthetic recovered read verdict.',
                    'evidence': {'read': verdict},
                }

            strategy['reconcile'] = recovered_result
            with patch.object(
                type(Dispatch), '_get_reconciliation_strategies',
                return_value={attempt.mutation_domain: strategy},
            ):
                reconciliation = (
                    Dispatch._recover_committed_attempt_to_reconciliation(
                        job,
                        attempt,
                        'post_c2_owner_recovery',
                        'dispatcher_recovery',
                    )
                )
                self.assertEqual(attempt.observed_outcome, 'uncertain')
                self.assertFalse(attempt.resolved_at)
                self.assertTrue(
                    attempt.remote_evidence_refs['recovery']
                )
                self.assertEqual(self.Job.search_count([
                    ('mutation_attempt_id', '=', attempt.id),
                ]), 1)
                self.assertFalse(job.current_attempt_token)
                self.assertFalse(job.owner_worker_ref)
                self.assertFalse(job.running_since)
                reconciliation.sudo().write({
                    'state': 'running',
                    'started_at': fields.Datetime.now(),
                })
                Dispatch._handle_mutation_dispatch_selftest_reconcile(
                    reconciliation
                )
            transport.assert_not_called()
            self.assertEqual(attempt.effective_disposition(), disposition)
            self.assertEqual(job.state, expected_state)
            self.assertEqual(reconciliation.state, 'succeeded')
