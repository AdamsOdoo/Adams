import ast
import os
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


FIXED_ERROR_CLASS_VOCABULARY = frozenset((
    'shopify_user_errors_validation',
    'inventory_location_missing',
    'concurrency_race_conflict',
    'shopify_throttling_rate_limit',
    'shopify_temporary_server_network',
    'data_shape_schema_mismatch',
    'idempotency_contract_violation',
    'no_reconciliation_strategy',
    'store_identity_mismatch',
))
WITHDRAWN_ERROR_CLASS_VALUES = frozenset((
    'remote_validation_rejected',
    'remote_precondition_mismatch',
    'transport_ambiguous',
    'clean_rejection',
))


class TestInventoryPushMechanics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Push Mechanics Test Store',
            'shop_domain': 'push-mechanics-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'Push Mechanics Location',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.mapping = cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/500',
            'odoo_location_id': cls.location.id,
            'match_key': 'manual',
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Push Mechanics Product',
        })
        cls.template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/500',
            'product_template_id': cls.template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/500',
            'product_variant_id': cls.template.product_variant_id.id,
            'product_template_binding_id': cls.template_binding.id,
        })
        cls.binding = cls.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'product_variant_binding_id': cls.variant_binding.id,
            'location_mapping_id': cls.mapping.id,
            'shopify_inventory_item_gid': 'gid://shopify/InventoryItem/500',
            'first_push_state': 'confirmed',
            'pending_target_available': 10.0,
        })
        cls.pair_key = 'inventory_pair:%s:%s:%s' % (
            cls.store.id, cls.binding.shopify_inventory_item_gid,
            cls.mapping.shopify_gid,
        )
        cls.Service = cls.env['shopify.connector.inventory.service']
        cls.user_reviewer = cls.env['res.users'].create({
            'name': 'Push Mechanics Reviewer',
            'login': 'push_mechanics_reviewer',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_reviewer'
                ).id,
            ])],
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Push Mechanics Operator',
            'login': 'push_mechanics_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _make_mutation_job(self, job_type, cas_retry_ordinal=0):
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': job_type,
            'state': 'queued',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': self.binding.id,
            'shopify_target_gid': self.pair_key,
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': self.store.connection_generation,
            'cas_retry_ordinal': cas_retry_ordinal,
        })
        token = uuid.uuid4().hex
        job.sudo().write({
            'state': 'running',
            'current_attempt_token': token,
            'started_at': fields.Datetime.now(),
            'running_since': fields.Datetime.now(),
        })
        return job, token

    def _make_attempt(
        self, job, token, target_quantity=10.0, change_from_quantity=5.0,
    ):
        side_context = dict(self.env.context)
        side_context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
        Attempt = self.env['shopify.connector.mutation.attempt'].with_context(
            side_context
        )
        preconditions = {
            'inventory_item_gid': self.binding.shopify_inventory_item_gid,
            'location_gid': self.mapping.shopify_gid,
            'target_quantity': target_quantity,
            'change_from_quantity': change_from_quantity,
            'snapshot_taken_at': fields.Datetime.to_string(
                fields.Datetime.now()
            ),
        }
        return Attempt._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': preconditions,
            'business_intent_fingerprint': 'bif-%s' % token,
            'exact_request_fingerprint': 'erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        })

    # ------------------------------------------------------------------
    # Fresh CAS pre-read / idempotency-key ownership
    # ------------------------------------------------------------------

    def test_cas_prepare_uses_fresh_read_not_binding_field(self):
        self.binding.sudo().write({'last_known_shopify_available': 999.0})
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'available': 3.0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ) as mocked_read:
            request = self.Service._prepare_preconditions_set_quantities(
                {
                    'job_id': job.id, 'store_id': self.store.id,
                    'binding_id': self.binding.id,
                    'inventory_item_gid':
                        self.binding.shopify_inventory_item_gid,
                    'location_gid': self.mapping.shopify_gid,
                    'expected_connection_generation':
                        job.expected_connection_generation,
                    'expected_store_identity': self.store.shop_domain,
                },
                {},
            )
        mocked_read.assert_called_once()
        self.assertEqual(
            request['preconditions_snapshot']['change_from_quantity'], 3.0,
        )
        self.assertEqual(
            request['variables']['input']['quantities'][0]['compareQuantity'],
            3.0,
        )

    def test_idempotency_key_lives_only_on_attempt(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        self.assertTrue(attempt.shopify_idempotency_key)
        self.assertNotIn(
            'shopify_idempotency_key', self.binding._fields,
        )
        self.assertNotIn(
            'last_push_idempotency_key', self.binding._fields,
        )

    # ------------------------------------------------------------------
    # Three-job model / one-attempt-per-job-lifetime
    # ------------------------------------------------------------------

    def test_job_type_equals_mutation_domain_for_both_mutation_jobs(self):
        for job_type in ('inventory_activate', 'inventory_set_quantities'):
            job, token = self._make_mutation_job(job_type)
            attempt = self._make_attempt(job, token)
            self.assertEqual(attempt.mutation_domain, job.job_type)

    def test_activation_and_set_quantities_are_distinct_jobs(self):
        activate_job, activate_token = self._make_mutation_job(
            'inventory_activate'
        )
        set_job, set_token = self._make_mutation_job(
            'inventory_set_quantities'
        )
        activate_attempt = self._make_attempt(activate_job, activate_token)
        set_attempt = self._make_attempt(set_job, set_token)
        self.assertNotEqual(activate_job.id, set_job.id)
        self.assertNotEqual(activate_job.job_type, set_job.job_type)
        self.assertNotEqual(
            activate_attempt.attempt_token, set_attempt.attempt_token,
        )
        self.assertNotEqual(
            activate_attempt.shopify_idempotency_key,
            set_attempt.shopify_idempotency_key,
        )

    def test_one_attempt_per_job_lifetime_enforced(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        self._make_attempt(job, token)
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._make_attempt(job, uuid.uuid4().hex)

    def test_explicit_activation_available_zero(self):
        request = self.Service._prepare_preconditions_activate(
            {
                'job_id': 1, 'store_id': self.store.id,
                'binding_id': self.binding.id,
                'inventory_item_gid':
                    self.binding.shopify_inventory_item_gid,
                'location_gid': self.mapping.shopify_gid,
                'expected_connection_generation': 0,
                'expected_store_identity': self.store.shop_domain,
            },
            {},
        )
        self.assertIn('available: 0', request['operation'])
        self.assertNotIn('onHand', request['operation'])

    # ------------------------------------------------------------------
    # CAS bounded 3-replacement chain
    # ------------------------------------------------------------------

    def test_cas_stale_bounded_replacement_chain_four_distinct_jobs(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=0,
        )
        self._make_attempt(job, token)
        chain = [job]
        for expected_ordinal in (0, 1, 2):
            current = chain[-1]
            attempt_for_current = self.env[
                'shopify.connector.mutation.attempt'
            ].search([('job_id', '=', current.id)])
            attempt_for_current._record_direct_outcome('failed_clean')
            self.Service._apply_consequence_set_quantities(
                current, attempt_for_current, 'direct',
                {
                    'observed_outcome': 'failed_clean',
                    'error_class': 'concurrency_race_conflict',
                    'manual_review_subreason': False,
                    'action': 'domain_callback',
                    'message': 'CAS stale.',
                    'evidence': {},
                    'domain_payload': {'reason': 'cas_stale'},
                },
            )
            current.invalidate_recordset()
            self.assertEqual(current.state, 'cancelled')
            self.assertEqual(
                current.cancel_reason, 'cas_stale_bounded_replacement',
            )
            self.assertTrue(current.superseded_by_job_id)
            new_job = current.superseded_by_job_id
            self.assertEqual(new_job.cas_retry_ordinal, expected_ordinal + 1)
            self.assertNotEqual(new_job.id, current.id)
            new_job.sudo().write({
                'current_attempt_token': uuid.uuid4().hex,
            })
            self._make_attempt(new_job, new_job.current_attempt_token)
            chain.append(new_job)

        # Fourth mismatch, at ordinal 3: no replacement job, blocked review.
        exhausted = chain[-1]
        self.assertEqual(exhausted.cas_retry_ordinal, 3)
        exhausted_attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].search([('job_id', '=', exhausted.id)])
        exhausted_attempt._record_direct_outcome('failed_clean')
        self.Service._apply_consequence_set_quantities(
            exhausted, exhausted_attempt, 'direct',
            {
                'observed_outcome': 'failed_clean',
                'error_class': 'concurrency_race_conflict',
                'manual_review_subreason': False,
                'action': 'domain_callback',
                'message': 'CAS stale.',
                'evidence': {},
                'domain_payload': {'reason': 'cas_stale'},
            },
        )
        exhausted.invalidate_recordset()
        self.assertEqual(exhausted.state, 'blocked_manual_review')
        self.assertEqual(exhausted.error_class, 'concurrency_race_conflict')
        self.assertEqual(exhausted.manual_review_subreason, 'binding_conflict')
        self.assertFalse(exhausted.superseded_by_job_id)
        self.assertEqual(len(set(j.id for j in chain)), 4)

    # ------------------------------------------------------------------
    # Reconciliation not_applied -> new job (both domains); blocked jobs
    # create no automatic child.
    # ------------------------------------------------------------------

    def test_reconciliation_not_applied_creates_new_set_quantities_job(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        self.Service._apply_consequence_set_quantities(
            job, attempt, 'reconciliation',
            {
                'observed_outcome': 'uncertain', 'error_class': False,
                'manual_review_subreason': False,
                'action': 'domain_callback', 'message': 'Not applied.',
                'evidence': {},
            },
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(
            job.cancel_reason, 'reconciliation_not_applied_replacement',
        )
        self.assertTrue(job.superseded_by_job_id)
        self.assertEqual(
            job.superseded_by_job_id.job_type, 'inventory_set_quantities',
        )

    def test_reconciliation_not_applied_creates_new_activate_job(self):
        job, token = self._make_mutation_job('inventory_activate')
        attempt = self._make_attempt(job, token)
        self.Service._apply_consequence_activate(
            job, attempt, 'reconciliation',
            {
                'observed_outcome': 'uncertain', 'error_class': False,
                'manual_review_subreason': False,
                'action': 'domain_callback', 'message': 'Not applied.',
                'evidence': {},
            },
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(
            job.cancel_reason, 'reconciliation_not_applied_replacement',
        )
        self.assertEqual(
            job.superseded_by_job_id.job_type, 'inventory_activate',
        )

    def test_blocked_manual_review_creates_no_automatic_child(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self.Service._apply_consequence_set_quantities(
            job, attempt, 'direct',
            {
                'observed_outcome': 'failed_clean',
                'error_class': 'inventory_location_missing',
                'manual_review_subreason': 'inventory_location_missing',
                'action': 'block_manual_review',
                'message': 'ITEM_NOT_STOCKED_AT_LOCATION.',
                'evidence': {},
            },
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(job.superseded_by_job_id)
        children = self.env['shopify.connector.job'].search([
            ('res_id', '=', self.binding.id),
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('id', '!=', job.id),
        ])
        self.assertFalse(children)

    # ------------------------------------------------------------------
    # Successful activation -> atomic fresh orchestration handoff
    # ------------------------------------------------------------------

    def test_activation_success_handoff_creates_fresh_push_sync(self):
        job, token = self._make_mutation_job('inventory_activate')
        attempt = self._make_attempt(job, token)
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        self.Service._apply_consequence_activate(
            job, attempt, 'direct',
            {
                'observed_outcome': 'succeeded', 'error_class': False,
                'manual_review_subreason': False, 'action': 'succeed',
                'message': 'Activated.', 'evidence': {},
            },
        )
        fresh = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertTrue(fresh)
        self.assertFalse(job.superseded_by_job_id)
        self.assertFalse(job.cancel_reason)

    # ------------------------------------------------------------------
    # Classification correctness
    # ------------------------------------------------------------------

    def test_throttled_classification(self):
        result = {
            'outcome': 'uncertain',
            'error_class': 'shopify_throttling_rate_limit',
            'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'shopify_throttling_rate_limit',
        )
        self.assertEqual(consequence['action'], 'reconcile')

    def test_change_from_quantity_stale_classification(self):
        result = {
            'user_errors': [{
                'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': [],
                'message': 'stale',
            }],
            'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'failed_clean')
        self.assertEqual(
            consequence['error_class'], 'concurrency_race_conflict',
        )
        self.assertEqual(consequence['action'], 'domain_callback')

    def test_item_not_stocked_at_location_classification(self):
        result = {
            'user_errors': [{
                'code': 'ITEM_NOT_STOCKED_AT_LOCATION', 'field': [],
                'message': 'not stocked',
            }],
            'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(
            consequence['error_class'], 'inventory_location_missing',
        )
        self.assertEqual(
            consequence['manual_review_subreason'],
            'inventory_location_missing',
        )
        self.assertEqual(consequence['action'], 'block_manual_review')

    def test_activate_never_routes_on_message_text(self):
        """inventoryActivate classification uses payload shape only --
        never `UserError.message` text, even when the message text
        happens to resemble a known code."""
        result = {
            'user_errors': [{
                'field': [], 'message': 'CHANGE_FROM_QUANTITY_STALE',
            }],
            'inventory_level': None,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(
            consequence['error_class'], 'shopify_user_errors_validation',
        )
        self.assertNotEqual(
            consequence['error_class'], 'concurrency_race_conflict',
        )

    def test_store_identity_mismatch_routes_reconciliation_job(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        self._make_attempt(job, token)
        attempt = self.env['shopify.connector.mutation.attempt'].search(
            [('job_id', '=', job.id)],
        )
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'available': 10.0, 'updated_at': False,
                'store_identity': 'a-different-shop.myshopify.com',
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'not_applied')
        self.assertEqual(result['error_class'], 'store_identity_mismatch')

    def test_aba_freshness_protects_not_applied_verdict(self):
        """A same-value read with a LATER updatedAt than transport must
        never be read as proof of not-applied."""
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        later_than_transport = fields.Datetime.to_string(
            fields.Datetime.now()
        )
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'available': 5.0,
                'updated_at': later_than_transport,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_applied_verdict_has_no_updated_at_condition(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'available': 10.0,
                'updated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'applied')

    # ------------------------------------------------------------------
    # action_recheck_inventory_pair -- positive/negative release classes
    # ------------------------------------------------------------------

    def _block_job_with(self, job, error_class, subreason, cas_retry_ordinal=None):
        if cas_retry_ordinal is not None:
            job.sudo().write({'cas_retry_ordinal': cas_retry_ordinal})
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': error_class,
            'manual_review_subreason': subreason,
            'finished_at': fields.Datetime.now(),
        })

    def test_release_positive_location_missing(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'Location now stocked, please re-check.'
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(job.cancel_reason, 'manual_review_release')

    def test_release_positive_ordinary_validation_conflict(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'shopify_user_errors_validation', 'binding_conflict',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'Corrected upstream, please re-check.'
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')

    def test_release_positive_cas_exhaustion_ordinal_three(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'CAS exhausted, releasing per DEC-037 §5.5(c).'
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(job.cancel_reason, 'manual_review_release')
        new_job = job.superseded_by_job_id
        self.assertEqual(new_job.job_type, 'inventory_push_sync')

    def test_release_never_rewrites_outcome_or_disposition(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'Release.'
        )
        attempt.invalidate_recordset()
        self.assertEqual(attempt.observed_outcome, 'failed_clean')
        self.assertFalse(attempt.resolution_disposition)

    def test_release_denied_for_operator(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        with self.assertRaises(AccessError):
            self.binding.with_user(
                self.user_operator
            ).action_recheck_inventory_pair('reason')

    def test_release_denied_without_reason(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('   ')

    def test_release_denied_for_uncertain(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('uncertain')
        self._block_job_with(job, 'duplicate_risk', 'duplicate_risk')
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('reason')

    def test_release_denied_for_store_identity_mismatch(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'store_identity_mismatch', 'store_identity_mismatch',
        )
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('reason')

    def test_release_denied_for_cas_ordinal_below_three(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=1,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('reason')

    def test_release_requires_exactly_one_blocked_job(self):
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('reason')

    # ------------------------------------------------------------------
    # Static/AST guards
    # ------------------------------------------------------------------

    def _service_source_tree(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_inventory_service.py',
        )
        with open(path, encoding='utf-8') as source_file:
            source = source_file.read()
        return source, ast.parse(source, filename=path)

    def test_no_error_class_value_outside_fixed_vocabulary(self):
        source, tree = self._service_source_tree()
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in FIXED_ERROR_CLASS_VOCABULARY:
                    found.add(node.value)
                self.assertNotIn(
                    node.value, WITHDRAWN_ERROR_CLASS_VALUES,
                    'Withdrawn error_class literal found: %r' % node.value,
                )

    def test_no_quantities_array_length_greater_than_one(self):
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'available': 3.0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            request = self.Service._prepare_preconditions_set_quantities(
                {
                    'job_id': 1, 'store_id': self.store.id,
                    'binding_id': self.binding.id,
                    'inventory_item_gid':
                        self.binding.shopify_inventory_item_gid,
                    'location_gid': self.mapping.shopify_gid,
                    'expected_connection_generation': 0,
                    'expected_store_identity': self.store.shop_domain,
                },
                {},
            )
        self.assertEqual(
            len(request['variables']['input']['quantities']), 1,
        )

    def test_no_inventory_activate_call_site_in_set_quantities_handler(self):
        source, tree = self._service_source_tree()
        methods = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        set_quantities_methods = [
            methods[name] for name in (
                '_prepare_local_set_quantities',
                '_prepare_preconditions_set_quantities',
                '_transport_set_quantities',
                '_classify_direct_set_quantities',
                '_reconcile_set_quantities',
                '_apply_consequence_set_quantities',
            )
        ]
        for method in set_quantities_methods:
            method_source = ast.get_source_segment(source, method) or ''
            self.assertNotIn('inventoryActivate', method_source, method.name)

        activate_methods = [
            methods[name] for name in (
                '_prepare_local_activate',
                '_prepare_preconditions_activate',
                '_transport_activate',
                '_classify_direct_activate',
                '_reconcile_activate',
                '_apply_consequence_activate',
            )
        ]
        for method in activate_methods:
            method_source = ast.get_source_segment(source, method) or ''
            self.assertNotIn(
                'inventorySetQuantities', method_source, method.name,
            )

    def test_no_message_text_matching_for_activate_classification(self):
        """Classification of `inventoryActivate` must use payload shape
        (`user_errors`/`inventory_level` truthiness) only -- the method
        may still emit its own fixed, human-readable 'message' key on
        the returned consequence dict, but it must never *read* a
        Shopify-supplied error message to decide the classification."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_classify_direct_activate'
        )
        method_source = ast.get_source_segment(source, method) or ''
        for forbidden in (".get('message')", '["message"]', "['message']"):
            self.assertNotIn(forbidden, method_source)

    def test_no_inventory_adjust_quantities_call(self):
        source, _tree = self._service_source_tree()
        self.assertNotIn('inventoryAdjustQuantities', source)

    def test_committed_never_written(self):
        source, _tree = self._service_source_tree()
        self.assertNotIn("'committed'", source)
