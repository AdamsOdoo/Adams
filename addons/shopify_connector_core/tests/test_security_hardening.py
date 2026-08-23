import json
import uuid
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_job import (
    JOB_STATE_SELECTION,
    LEGAL_JOB_TRANSITIONS,
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
class TestSecurityHardening(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'SEC-1 core test store',
            'shop_domain': 'sec1-core.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.Enqueue = cls.env['shopify.connector.job.enqueue']
        cls.roles = {
            label: cls._role_user(label, xmlid)
            for label, xmlid in (
                ('auditor', 'group_shopify_connector_auditor'),
                ('operator', 'group_shopify_connector_operator'),
                ('reviewer', 'group_shopify_connector_reviewer'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }
        cls.plain_user = cls._role_user(False, False)

    @classmethod
    def _role_user(cls, label, group_xmlid):
        groups = [cls.env.ref('base.group_user').id]
        if group_xmlid:
            groups.append(
                cls.env.ref('shopify_connector_core.%s' % group_xmlid).id,
            )
        return cls.env['res.users'].create({
            'name': 'SEC-1 core %s' % (label or 'plain'),
            'login': 'sec1_core_%s' % (label or 'plain'),
            'group_ids': [(6, 0, groups)],
        })

    def _job(self, state='queued', **extra):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        }
        if state == 'blocked_manual_review':
            values.update({
                'error_class': 'duplicate_risk',
                'manual_review_subreason': 'duplicate_risk',
            })
        values.update(extra)
        job = self.Job.sudo().create(values)
        return self.Job.browse(job.id)

    def _logs(self, job, event_type=False):
        domain = [('job_id', '=', job.id)]
        if event_type:
            domain.append(('event_type', '=', event_type))
        return self.JobLog.search(domain)

    def test_privileged_cron_services_refuse_direct_rpc_by_non_admin(self):
        services = (
            self.env['shopify.connector.job.dispatch'],
            self.env['shopify.connector.pii.retention'],
            self.env['shopify.connector.stale.owner.sweep'],
        )
        denied = [self.plain_user] + [
            self.roles[label]
            for label in ('auditor', 'operator', 'reviewer')
        ]
        for service in services:
            for user in denied:
                with self.assertRaises(
                    AccessError, msg=(service._name, user.login),
                ):
                    caller = service.with_user(user)
                    if service._name == 'shopify.connector.job.dispatch':
                        caller.run_drain(limit=1)
                    else:
                        caller.run_sweep()

        self.assertEqual(
            self.env['shopify.connector.job.dispatch'].with_user(
                self.roles['admin']
            ).run_drain(limit=1),
            0,
        )
        self.assertEqual(
            self.env['shopify.connector.pii.retention'].with_user(
                self.roles['admin']
            ).run_sweep(),
            True,
        )
        self.assertEqual(
            self.env['shopify.connector.stale.owner.sweep'].with_user(
                self.roles['admin']
            ).run_sweep(),
            0,
        )
        self.assertEqual(
            self.env['shopify.connector.job.dispatch'].sudo().run_drain(
                limit=1,
            ),
            0,
        )
        self.assertEqual(
            self.env['shopify.connector.pii.retention'].sudo().run_sweep(),
            True,
        )
        self.assertEqual(
            self.env[
                'shopify.connector.stale.owner.sweep'
            ].sudo().run_sweep(),
            0,
        )

    def test_protected_job_write_denied_for_all_four_roles(self):
        for label, user in self.roles.items():
            for values in (
                {'state': 'cancelled'},
                {'retry_count': 99},
                {'error_class': 'unknown_system_error'},
                {'original_job_type': 'forged'},
                {'cancel_reason': 'forged'},
            ):
                job = self._job()
                before = job.read(list(values))[0]
                with self.assertRaises(AccessError, msg=(label, values)):
                    job.with_user(user).write(values)
                job.invalidate_recordset()
                self.assertEqual(job.read(list(values))[0], before)

    def test_direct_create_and_unlink_denied_for_all_four_roles(self):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'succeeded',
            'payload_hash': str(uuid.uuid4()),
            'original_job_type': 'forged',
        }
        for label, user in self.roles.items():
            with self.assertRaises(AccessError, msg=label):
                self.Job.with_user(user).create(dict(values))
            job = self._job()
            with self.assertRaises(AccessError, msg=label):
                job.with_user(user).unlink()
            self.assertTrue(job.exists())

    def test_sanctioned_create_preserves_original_type_anti_spoof(self):
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'original_job_type': 'forged',
        })
        self.assertEqual(job.original_job_type, 'core_dispatch_selftest')

    def _transition_values(self, from_state, to_state):
        values = {'state': to_state}
        if to_state == 'blocked_manual_review':
            values.update({
                'error_class': 'duplicate_risk',
                'manual_review_subreason': 'duplicate_risk',
            })
        elif from_state == 'blocked_manual_review':
            values['manual_review_subreason'] = False
        return values

    def test_exhaustive_transition_matrix_for_sudo_callers(self):
        states = [value for value, _label in JOB_STATE_SELECTION]
        for from_state in states:
            for to_state in states:
                if from_state == to_state:
                    continue
                job = self._job(from_state)
                values = self._transition_values(from_state, to_state)
                if to_state in LEGAL_JOB_TRANSITIONS[from_state]:
                    job.sudo().write(values)
                    self.assertEqual(job.state, to_state)
                else:
                    with self.assertRaises(
                        ValidationError,
                        msg='%s -> %s' % (from_state, to_state),
                    ):
                        job.sudo().write(values)
                    job.invalidate_recordset()
                    self.assertEqual(job.state, from_state)

    def test_recovery_edges_exact_without_legalizing_draft_or_rpc_writes(self):
        self.assertEqual(
            LEGAL_JOB_TRANSITIONS['queued'],
            frozenset((
                'running', 'cancelled', 'failed_retryable',
                'retry_waiting', 'failed_final', 'blocked_manual_review',
            )),
        )
        self.assertEqual(
            LEGAL_JOB_TRANSITIONS['retry_waiting'],
            frozenset((
                'running', 'cancelled', 'failed_retryable',
                'failed_final', 'blocked_manual_review',
            )),
        )
        self.assertNotIn('running', LEGAL_JOB_TRANSITIONS['draft'])
        self.assertNotIn('retry_waiting', LEGAL_JOB_TRANSITIONS['draft'])

        for target in ('running', 'retry_waiting'):
            job = self._job('draft')
            with self.assertRaises(ValidationError, msg=target):
                job.sudo().write({'state': target})
            job.invalidate_recordset()
            self.assertEqual(job.state, 'draft')

        for label, user in self.roles.items():
            job = self._job('queued')
            with self.assertRaises(AccessError, msg=label):
                job.with_user(user).write({'state': 'retry_waiting'})
            job.invalidate_recordset()
            self.assertEqual(job.state, 'queued')

    def test_resolve_manual_review_role_state_and_audit(self):
        job = self._job('blocked_manual_review')
        with self.assertRaises(AccessError):
            job.with_user(self.roles['operator']).action_resolve_manual_review()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(self._logs(job, 'manual_action'))

        job.with_user(self.roles['admin']).action_resolve_manual_review()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        self.assertFalse(job.manual_review_subreason)
        logs = self._logs(job, 'manual_action')
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.actor_uid, self.roles['admin'])

        illegal = self._job('failed_retryable')
        with self.assertRaises(UserError):
            illegal.with_user(
                self.roles['admin']
            ).action_resolve_manual_review()
        self.assertEqual(illegal.state, 'failed_retryable')
        self.assertFalse(self._logs(illegal, 'manual_action'))

    def test_lifecycle_conversion_is_sanctioned_after_direct_denial(self):
        job = self._job('queued')
        operator_job = job.with_user(self.roles['operator'])
        with self.assertRaises(AccessError):
            operator_job.write({'original_job_type': 'forged'})
        operator_job._reassign_to_historic_job_type()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(job.job_type, 'historic_domain_job')
        self.assertEqual(job.original_job_type, 'core_dispatch_selftest')
        logs = self._logs(job, 'manual_action')
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.actor_uid, self.roles['operator'])

    def test_enqueue_is_sanctioned_and_does_not_return_sudo_record(self):
        self.store.write({'state': 'connected'})
        job = self.Enqueue.with_user(self.roles['operator']).enqueue(
            self.store.with_user(self.roles['operator']),
            'manual_sync',
            'core_dispatch_selftest',
            payload_hash=str(uuid.uuid4()),
        )
        self.assertEqual(job.state, 'queued')
        self.assertFalse(job.env.su)
        with self.assertRaises(AccessError):
            job.write({'retry_count': 10})

    def test_lifecycle_audit_helper_preserves_actor_and_one_carrier(self):
        admin = self.roles['admin']
        before_jobs = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        job = self.store.with_user(admin)._create_lifecycle_audit_job(
            'SEC-1 identifiers-only audit actor_uid=%d' % admin.id
        )
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(
            self.Job.search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'core_manual_maintenance'),
            ]),
            before_jobs + 1,
        )
        logs = self._logs(job, 'manual_action')
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.actor_uid, admin)

    def test_retention_redacts_payload_and_one_summary_per_affected_store(self):
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store.id,
            'log_redaction_retention_days': 1,
        })
        job = self._job('succeeded')
        old = fields.Datetime.now() - timedelta(days=2)
        log = self.JobLog.sudo().create({
            'job_id': job.id,
            'event_type': 'note',
            'message': 'old payload fixture',
            'payload_snapshot': json.dumps({
                'email': 'raw@example.com',
                'nested': {'phone': '+971501234567', 'count': 2},
            }),
            'actor_uid': self.env.uid,
            'occurred_at': old,
        })
        before = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        self.env['shopify.connector.pii.retention'].run_sweep()
        log.invalidate_recordset()
        self.assertNotIn('raw@example.com', log.payload_snapshot)
        self.assertNotIn('+971501234567', log.payload_snapshot)
        payload = json.loads(log.payload_snapshot)
        self.assertEqual(payload['email'], '***')
        self.assertEqual(payload['nested']['phone'], '***')
        audits = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        self.assertEqual(len(audits), before + 1)
        summary = audits[-1]
        summary_logs = self._logs(summary, 'manual_action')
        self.assertEqual(len(summary_logs), 1)
        self.assertNotIn('raw@example.com', summary_logs.message)
        self.assertIn('redacted_payload_count=1', summary_logs.message)
