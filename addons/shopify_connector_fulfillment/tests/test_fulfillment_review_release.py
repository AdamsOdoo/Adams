import json
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
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
class TestFulfillmentReviewRelease(TransactionCase):
    """Mode 1 review-case actions + the review-release sanctioned helper
    (DEC-038 §7.3).

    action_acknowledge_external marks the evidence acknowledged; action_import_
    tracking writes carrier tracking onto the order's outgoing picking (a
    non-stock write). _release_blocked_mutation releases exactly one eligible
    blocked mutation: a synchronous clean rejection (failed_clean, effective
    not_applied) or a pre-C2 job with no attempt is eligible and gets a
    manual_sync + empty-trigger-origin replacement under lineage; a post-C2
    uncertain attempt is reconcile-only and never resent. The release helper
    and acknowledgement are Administrator-gated; importing tracking remains
    routine Operator/User work.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Binding = cls.env['shopify.connector.fulfillment.binding']
        cls.Evidence = cls.env['shopify.connector.fulfillment.inbound.evidence']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'P1', 'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.order_binding = cls.env['shopify.connector.order.binding'].sudo().create({
            'store_id': cls.store.id, 'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id, 'status': 'active',
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.pt_out = cls.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.pt_out.id,
            'location_id': cls.stock_loc.id,
            'location_dest_id': cls.customer_loc.id,
            'sale_id': cls.sale.id,
        })
        # Release and acknowledgement are Administrator-gated. Importing
        # tracking remains routine Operator/Admin work.
        cls.reviewer_user = cls.env['res.users'].create({
            'name': 'FUL reviewer',
            'login': 'ful_reviewer_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin',
                ).id,
            ])],
        })
        cls.plain_user = cls.env['res.users'].create({
            'name': 'FUL plain',
            'login': 'ful_plain_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.connector_user = cls.env['res.users'].create({
            'name': 'FUL connector user',
            'login': 'ful_connector_user_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_user',
                ).id,
            ])],
        })

    # ------------------------------------------------------------------
    # Fixture builders
    # ------------------------------------------------------------------

    def _evidence(self, **overrides):
        vals = {
            'store_id': self.store.id,
            'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/%s' % uuid.uuid4().hex[:8],
            'order_binding_id': self.order_binding.id,
            'origin_class': 'external_merchant',
            'origin_confirmed': True,
            'reconciled_state': 'review',
            'review_reason': 'remote_state_changed',
        }
        vals.update(overrides)
        return self.Evidence.sudo().create(vals)

    def _blocked_tracking(self, outcome, blocked_state):
        """Build a fulfillment binding + a blocked fulfillment_tracking_update
        mutation job whose one post-C2 attempt carries `outcome`.

        NOTE: the eligible-replacement path supersedes (cancels) the blocked
        job, and `failed_final -> cancelled` is not a legal job transition
        (LEGAL_JOB_TRANSITIONS); the eligible case therefore uses a
        cancel-legal blocked state (failed_retryable), while the never-eligible
        uncertain case (which raises before any transition) uses failed_final.
        """
        binding = self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/%s' % uuid.uuid4().hex[:8],
            'picking_id': self.picking.id,
            'order_binding_id': self.order_binding.id,
            'status': 'active',
        })
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': 'fulfillment_tracking_change',
            'job_type': 'fulfillment_tracking_update',
            'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.binding',
            'res_id': binding.id,
            'shopify_target_gid': binding.shopify_gid,
            'payload_hash': uuid.uuid4().hex,
        })
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'fulfillment_tracking_update',
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {},
            'preconditions_snapshot': {'fulfillment_gid': binding.shopify_gid},
            'business_intent_fingerprint': 'bif',
            'exact_request_fingerprint': 'erf',
            'shopify_idempotency_key': '',
        })
        attempt._record_direct_outcome(outcome, evidence={})
        job.sudo().write({
            'state': blocked_state,
            'error_class': 'shopify_user_errors_validation',
            'finished_at': fields.Datetime.now(),
        })
        return binding, job, attempt

    def _tracking_update_jobs(self, binding):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'fulfillment_tracking_update'),
            ('res_model', '=', 'shopify.connector.fulfillment.binding'),
            ('res_id', '=', binding.id),
        ])

    # ------------------------------------------------------------------
    # Mode 1 review-case actions on the evidence
    # ------------------------------------------------------------------

    def test_acknowledge_external_sets_acknowledged(self):
        evidence = self._evidence()
        evidence.with_user(self.reviewer_user).action_acknowledge_external()
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'acknowledged')

    def test_connector_user_cannot_acknowledge_external_review(self):
        evidence = self._evidence()
        with self.assertRaises(AccessError):
            evidence.with_user(self.connector_user).action_acknowledge_external()
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'review')

    def test_import_tracking_writes_carrier_ref_non_stock(self):
        tracking = [{'number': '1Z999', 'url': 'http://track/1', 'company': 'UPS'}]
        evidence = self._evidence(tracking_snapshot=json.dumps(tracking))
        before_state = self.picking.state
        # The delivery-picking resolver traverses sale.picking_ids; supply the
        # resolved outgoing picking directly (the tracking write is what is
        # under test), mirroring the deterministic-selector stub pattern.
        with patch.object(
            type(self.Service), '_evidence_delivery_picking',
            return_value=self.picking,
        ):
            evidence.with_user(self.reviewer_user).action_import_tracking()
        self.picking.invalidate_recordset()
        self.assertEqual(self.picking.carrier_tracking_ref, '1Z999')
        # Odoo 19's carrier_tracking_url is a read-only computed field derived
        # from carrier_id + carrier_tracking_ref; the raw imported Shopify URL
        # is deliberately NOT persisted to it (the stored ref above is the
        # imported evidence). With no carrier on this picking it computes falsy.
        self.assertFalse(self.picking.carrier_tracking_url)
        # A non-stock write only: picking state is untouched.
        self.assertEqual(self.picking.state, before_state)
        evidence.invalidate_recordset()
        self.assertEqual(evidence.reconciled_state, 'acknowledged')

    # ------------------------------------------------------------------
    # Review-release sanctioned helper
    # ------------------------------------------------------------------

    def test_release_eligible_failed_clean_creates_manual_sync_replacement(self):
        binding, old_job, attempt = self._blocked_tracking(
            'failed_clean', 'failed_retryable',
        )
        self.assertEqual(attempt.effective_disposition(), 'not_applied')
        new_job = self.Service.with_user(self.reviewer_user)._release_blocked_mutation(
            binding.with_user(self.reviewer_user),
            'Clean synchronous rejection; please resend.',
        )
        # The replacement always uses manual_sync + empty trigger origin.
        self.assertEqual(new_job.job_source, 'manual_sync')
        self.assertFalse(new_job.trigger_origin)
        self.assertEqual(new_job.job_type, 'fulfillment_tracking_update')
        self.assertEqual(new_job.state, 'queued')
        # Exactly one replacement, and the predecessor is superseded/cancelled.
        old_job.invalidate_recordset()
        self.assertEqual(old_job.state, 'cancelled')
        self.assertEqual(old_job.superseded_by_job_id, new_job)
        self.assertNotEqual(new_job, old_job)

    def test_release_post_c2_uncertain_not_eligible_raises(self):
        binding, old_job, attempt = self._blocked_tracking(
            'uncertain', 'failed_final',
        )
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        with self.assertRaises(UserError):
            self.Service.with_user(self.reviewer_user)._release_blocked_mutation(
                binding.with_user(self.reviewer_user),
                'Attempt to resend an uncertain mutation.',
            )
        # No resend: the predecessor is untouched and nothing was superseded.
        old_job.invalidate_recordset()
        self.assertEqual(old_job.state, 'failed_final')
        self.assertFalse(old_job.superseded_by_job_id)
        self.assertEqual(self._tracking_update_jobs(binding), old_job)

    def test_release_requires_administrator(self):
        binding, old_job, attempt = self._blocked_tracking(
            'failed_clean', 'failed_retryable',
        )
        with self.assertRaises(AccessError):
            self.Service.with_user(self.plain_user)._release_blocked_mutation(
                binding.with_user(self.plain_user), 'Not authorized.',
            )
        # The blocked mutation is untouched by the refused release.
        old_job.invalidate_recordset()
        self.assertEqual(old_job.state, 'failed_retryable')
        self.assertEqual(self._tracking_update_jobs(binding), old_job)

    def test_release_empty_reason_rejected(self):
        binding, old_job, attempt = self._blocked_tracking(
            'failed_clean', 'failed_retryable',
        )
        with self.assertRaises(UserError):
            self.Service.with_user(self.reviewer_user)._release_blocked_mutation(
                binding.with_user(self.reviewer_user), '   ',
            )
