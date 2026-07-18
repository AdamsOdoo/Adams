from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError

from ..models.shopify_connector_order_importer import OrderPendingWait
from .test_order_import_mapping import OrderImportCase


class TestOrderManualGatewayOverlay(OrderImportCase):

    def _manual_payload(
        self, gid='gid://shopify/Order/Manual', gateway='Cash on Delivery',
        manual=True,
    ):
        payload = self._payload(gid, 'PENDING')
        payload['paymentGatewayNames'] = [gateway]
        payload['transactions'] = [self._transaction(
            gateway=gateway, manual=manual,
        )]
        return payload

    def _configure(self, policy='require_approval', approved='Cash on Delivery'):
        self.settings.write({
            'manual_gateway_policy': policy,
            'approved_manual_gateways': approved,
            'order_confirmation_policy': 'paid_only',
        })

    def test_gateway_diagnostic_evidence_redacts_every_string_surface(self):
        detail = self.Importer._safe_gateway_evidence({
            'paymentGatewayNames': ['buyer@example.invalid'],
            'transactions': [{
                'gateway': 'billing@example.invalid',
                'kind': 'owner@example.invalid',
                'status': '+971 50 123 4567',
                'manualPaymentGateway': True,
            }],
        })
        for secret in (
            'buyer@example.invalid', 'billing@example.invalid',
            'owner@example.invalid', '123 4567',
        ):
            self.assertNotIn(secret, detail)

    def test_all_manual_gateway_policies_and_cod_read_model(self):
        for policy, state, approval in (
            ('confirm_auto', 'sale', 'not_required'),
            ('quotation', 'draft', 'not_required'),
            ('require_approval', 'draft', 'pending'),
        ):
            self._configure(policy)
            payload = self._manual_payload(
                'gid://shopify/Order/Manual/%s' % policy,
            )
            binding = self.Importer._apply_import(self.store, payload)
            self.assertEqual(binding.sale_order_id.state, state)
            self.assertEqual(binding.manual_gateway_approval_state, approval)
            self.assertTrue(binding.is_cod)
            self.assertEqual(binding.cod_fulfillment_state, 'not_dispatched')
            self.assertEqual(binding.cod_collection_state, 'nothing_collected')
            self.assertEqual(binding.cod_collected_value_amount, '0')

    def test_unapproved_and_card_pending_never_take_manual_path(self):
        self._configure()
        for payload in (
            self._manual_payload(
                'gid://shopify/Order/Unapproved', gateway='Bank Deposit',
            ),
            self._manual_payload(
                'gid://shopify/Order/CardPending', gateway='shopify_payments',
                manual=False,
            ),
        ):
            orders_before = self.env['sale.order'].search_count([])
            with self.assertRaises(OrderPendingWait):
                self.Importer._apply_import(self.store, payload)
            self.assertEqual(
                self.env['sale.order'].search_count([]), orders_before,
            )
            self.assertFalse(self.Binding.search([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', payload['id']),
            ]))

    def test_mixed_transaction_imports_review_draft(self):
        self._configure('confirm_auto')
        payload = self._manual_payload('gid://shopify/Order/Mixed')
        payload['paymentGatewayNames'] = [
            'Cash on Delivery', 'shopify_payments',
        ]
        payload['transactions'].append(self._transaction(
            gateway='shopify_payments', manual=False, status='SUCCESS',
        ))
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.manual_gateway_evidence_state, 'mixed')
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertFalse(binding.is_cod)

    def test_malformed_transaction_authority_is_review_never_confirmation(self):
        self._configure('confirm_auto')
        payload = self._manual_payload('gid://shopify/Order/MalformedAuthority')
        payload['transactions'][0]['manualPaymentGateway'] = 'true'
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.manual_gateway_evidence_state, 'mixed')
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertFalse(binding.is_cod)

    def test_approval_permissions_reason_provenance_and_redaction(self):
        self._configure()
        payload = self._manual_payload('gid://shopify/Order/Approval')
        binding = self.Importer._apply_import(self.store, payload)
        reviewer = self.roles['reviewer']
        self.assertFalse(reviewer.has_group('sales_team.group_sale_salesman'))
        with self.assertRaises(AccessError):
            binding.sale_order_id.with_user(reviewer).check_access('read')
        for role in ('auditor', 'operator'):
            with self.assertRaises(AccessError, msg=role):
                binding.with_user(self.roles[role]).action_approve_manual_gateway_order(
                    'approve'
                )
        for reason in (False, '', '   '):
            with self.assertRaises(UserError):
                binding.with_user(reviewer).action_approve_manual_gateway_order(
                    reason
                )

        audit_before = self.Job.search_count([
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        refresh_before = self.Job.search_count([
            ('job_type', '=', 'order_import_sync'),
        ])
        approved_at = datetime(2026, 7, 17, 15, 30, 0)
        with patch.object(fields.Datetime, 'now', return_value=approved_at):
            binding.with_user(reviewer).action_approve_manual_gateway_order(
                'Approved by buyer@example.invalid +971 50 123 4567'
            )
        binding.invalidate_recordset()
        self.assertEqual(binding.manual_gateway_approved_at, approved_at)
        self.assertEqual(
            binding.manual_gateway_approved_by_uid, reviewer,
        )
        self.assertEqual(
            binding.manual_gateway_approved_shopify_updated_at,
            binding.shopify_updated_at_snapshot,
        )
        self.assertEqual(self.Job.search_count([
            ('job_type', '=', 'order_import_sync'),
        ]), refresh_before + 1)
        audits = self.Job.search([
            ('job_type', '=', 'core_manual_maintenance'),
        ], order='id desc', limit=1)
        self.assertEqual(self.Job.search_count([
            ('job_type', '=', 'core_manual_maintenance'),
        ]), audit_before + 1)
        logs = self.JobLog.search([('job_id', '=', audits.id)])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.actor_uid, reviewer)
        self.assertNotIn('buyer@example.invalid', logs.message)
        self.assertNotIn('123 4567', logs.message)

    def test_approval_refreshes_before_confirm_and_is_idempotent(self):
        self._configure()
        payload = self._manual_payload('gid://shopify/Order/ApprovalRefresh')
        binding = self.Importer._apply_import(self.store, payload)
        reviewer_binding = binding.with_user(self.roles['reviewer'])
        reviewer_binding.action_approve_manual_gateway_order('approved')
        job_count = self.Job.search_count([])
        audit_count = self.JobLog.search_count([
            ('event_type', '=', 'manual_action'),
        ])
        reviewer_binding.action_approve_manual_gateway_order('duplicate')
        self.assertEqual(self.Job.search_count([]), job_count)
        self.assertEqual(self.JobLog.search_count([
            ('event_type', '=', 'manual_action'),
        ]), audit_count)
        self.assertEqual(binding.sale_order_id.state, 'draft')

        self.Importer._apply_import(self.store, payload)
        binding.invalidate_recordset()
        self.assertEqual(binding.sale_order_id.state, 'sale')
        self.assertEqual(binding.manual_gateway_approval_state, 'approved')
        reviewer_binding.action_approve_manual_gateway_order('already approved')
        self.assertEqual(self.Job.search_count([]), job_count)

    def test_changed_evidence_supersedes_approval_without_confirming(self):
        self._configure()
        payload = self._manual_payload('gid://shopify/Order/StaleApproval')
        binding = self.Importer._apply_import(self.store, payload)
        binding.with_user(
            self.roles['admin']
        ).action_approve_manual_gateway_order('approved')
        payload['updatedAt'] = '2026-07-17T13:00:00Z'
        self.Importer._apply_import(self.store, payload)
        binding.invalidate_recordset()
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.manual_gateway_approval_state, 'superseded')

    def test_later_paid_evidence_reuses_binding_without_pending_approval(self):
        self._configure()
        payload = self._manual_payload('gid://shopify/Order/LaterPaid')
        binding = self.Importer._apply_import(self.store, payload)
        order_id = binding.sale_order_id.id
        payload['displayFinancialStatus'] = 'PAID'
        payload['updatedAt'] = '2026-07-17T14:00:00Z'
        same = self.Importer._apply_import(self.store, payload)
        same.invalidate_recordset()
        self.assertEqual(same, binding)
        self.assertEqual(same.sale_order_id.id, order_id)
        self.assertEqual(same.sale_order_id.state, 'sale')
        self.assertEqual(same.manual_gateway_approval_state, 'not_required')
        self.assertEqual(self.Binding.search_count([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', payload['id']),
        ]), 1)

    def test_paid_change_after_recorded_approval_stays_review_draft(self):
        self._configure()
        payload = self._manual_payload('gid://shopify/Order/PaidAfterApproval')
        binding = self.Importer._apply_import(self.store, payload)
        binding.with_user(
            self.roles['reviewer']
        ).action_approve_manual_gateway_order('approved pending evidence')
        payload['displayFinancialStatus'] = 'PAID'
        payload['updatedAt'] = '2026-07-17T14:30:00Z'
        self.Importer._apply_import(self.store, payload)
        binding.invalidate_recordset()
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.manual_gateway_approval_state, 'superseded')

    def test_atomic_rollback_when_audit_creation_fails(self):
        EnqueueType = type(self.env['shopify.connector.job.enqueue'])
        failure_sites = (
            (
                'enqueue', EnqueueType, 'enqueue',
                UserError('enqueue unavailable'),
            ),
            (
                'audit', type(self.store), '_create_lifecycle_audit_job',
                UserError('audit unavailable'),
            ),
        )
        for label, model_type, method_name, failure in failure_sites:
            with self.subTest(failure_site=label):
                self._configure()
                payload = self._manual_payload(
                    'gid://shopify/Order/AtomicRollback/%s' % label,
                )
                binding = self.Importer._apply_import(self.store, payload)
                jobs_before = self.Job.search_count([])
                logs_before = self.JobLog.search_count([])
                with patch.object(
                    model_type, method_name, side_effect=failure,
                ):
                    with self.assertRaises(UserError):
                        binding.with_user(
                            self.roles['reviewer']
                        ).action_approve_manual_gateway_order('approved')
                binding.invalidate_recordset()
                self.assertEqual(
                    binding.manual_gateway_approval_state, 'pending',
                )
                self.assertFalse(binding.manual_gateway_approved_at)
                self.assertFalse(binding.manual_gateway_approved_by_uid)
                self.assertEqual(self.Job.search_count([]), jobs_before)
                self.assertEqual(self.JobLog.search_count([]), logs_before)

    def test_policy_or_gateway_change_refuses_without_audit(self):
        scenarios = (
            ('policy', {'manual_gateway_policy': 'quotation'}, False),
            ('gateway', {'approved_manual_gateways': 'Bank Deposit'}, False),
            ('evidence', {}, {
                'manual_gateway_evidence_state': 'not_manual',
            }),
            ('mixed', {}, {
                'status': 'review',
                'manual_gateway_evidence_state': 'mixed',
            }),
            ('non_draft', {}, 'confirm'),
        )
        for label, settings_values, binding_setup in scenarios:
            with self.subTest(refusal=label):
                self._configure()
                payload = self._manual_payload(
                    'gid://shopify/Order/ApprovalRefusal/%s' % label,
                )
                binding = self.Importer._apply_import(self.store, payload)
                if settings_values:
                    self.settings.write(settings_values)
                if isinstance(binding_setup, dict):
                    binding.sudo().write(binding_setup)
                elif binding_setup == 'confirm':
                    binding.sale_order_id.action_confirm()
                jobs_before = self.Job.search_count([])
                logs_before = self.JobLog.search_count([])
                with self.assertRaises(UserError):
                    binding.with_user(
                        self.roles['admin']
                    ).action_approve_manual_gateway_order(
                        'stale approval evidence'
                    )
                binding.invalidate_recordset()
                self.assertFalse(binding.manual_gateway_approved_at)
                self.assertFalse(binding.manual_gateway_approved_by_uid)
                self.assertEqual(self.Job.search_count([]), jobs_before)
                self.assertEqual(self.JobLog.search_count([]), logs_before)

        self._configure()
        binding = self.Importer._apply_import(
            self.store,
            self._manual_payload(
                'gid://shopify/Order/ApprovalRefusal/company',
            ),
        )
        other_company = self.env['res.company'].sudo().create({
            'name': 'Manual Approval Other Company',
        })
        admin = self.roles['admin']
        admin.sudo().write({'company_ids': [(4, other_company.id)]})
        jobs_before = self.Job.search_count([])
        logs_before = self.JobLog.search_count([])
        with self.assertRaises(AccessError):
            binding.with_user(admin).with_company(
                other_company
            ).action_approve_manual_gateway_order('wrong company')
        binding.invalidate_recordset()
        self.assertFalse(binding.manual_gateway_approved_at)
        self.assertFalse(binding.manual_gateway_approved_by_uid)
        self.assertEqual(self.Job.search_count([]), jobs_before)
        self.assertEqual(self.JobLog.search_count([]), logs_before)
