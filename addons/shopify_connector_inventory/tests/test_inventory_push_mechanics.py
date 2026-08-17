import ast
import os
import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)
from odoo.addons.shopify_connector_inventory.models.shopify_connector_inventory_service import (
    InventoryActivationSupersededError,
    InventoryPreC2FailClosedError,
)
from odoo.tools import mute_logger


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
                    'shopify_connector_core.group_shopify_connector_admin'
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
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 3, 'updated_at': False,
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
            request['preconditions_snapshot']['change_from_quantity'], 3,
        )
        self.assertEqual(
            request['variables']['input']['quantities'][0][
                'changeFromQuantity'
            ],
            3,
        )
        self.assertNotIn(
            'compareQuantity',
            request['variables']['input']['quantities'][0],
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
            # Free the pair's operation_scope_key before the next job_type
            # creates its own (only one non-terminal pair job at a time).
            job.sudo().write({'state': 'cancelled', 'cancel_reason': 'test'})

    def test_activation_and_set_quantities_are_distinct_jobs(self):
        activate_job, activate_token = self._make_mutation_job(
            'inventory_activate'
        )
        activate_attempt = self._make_attempt(activate_job, activate_token)
        # A single pair may only hold one non-terminal pair-execution job at
        # a time (activation then set-quantities are serialized, never
        # simultaneous); terminalize the activation before the set job so
        # the two do not collide on the pair's operation_scope_key.
        activate_job.sudo().write({
            'state': 'cancelled', 'cancel_reason': 'test',
        })
        set_job, set_token = self._make_mutation_job(
            'inventory_set_quantities'
        )
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
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None, 'available': None,
                'updated_at': False, 'store_identity': self.store.shop_domain,
            },
        ):
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
        self.assertEqual(request['variables']['available'], 0)
        self.assertNotIn('onHand', request['operation'])
        self.assertIn('@idempotent(key: $idempotencyKey)', request['operation'])
        self.assertIn('$idempotencyKey: String!', request['operation'])
        self.assertIn('idempotencyKey', request['variables'])
        self.assertEqual(
            request['variables']['idempotencyKey'],
            request['shopify_idempotency_key'],
        )

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
            attempt_for_current._record_direct_outcome(
                'failed_clean',
                evidence={'user_errors': [
                    {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
                ]},
            )
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
            # The CAS successor is created queued; C2 attempt creation
            # requires a running job whose owner token matches, so promote
            # it exactly as the dispatcher would before its own attempt.
            new_job.sudo().write({
                'state': 'running',
                'current_attempt_token': uuid.uuid4().hex,
                'started_at': fields.Datetime.now(),
                'running_since': fields.Datetime.now(),
            })
            self._make_attempt(new_job, new_job.current_attempt_token)
            chain.append(new_job)

        # Fourth mismatch, at ordinal 3: no replacement job, blocked review.
        exhausted = chain[-1]
        self.assertEqual(exhausted.cas_retry_ordinal, 3)
        exhausted_attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].search([('job_id', '=', exhausted.id)])
        exhausted_attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
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
        # The core Layer-2 committer writes blocked_manual_review for a
        # block_manual_review disposition *before* invoking this domain
        # callback (job_dispatch `_commit`/`_apply` ordering); replicate
        # that seam so the callback is exercised exactly as in production
        # -- its own contract here is only that it adds no automatic child.
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': 'inventory_location_missing',
            'manual_review_subreason': 'inventory_location_missing',
            'finished_at': fields.Datetime.now(),
        })
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
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 10.0, 'updated_at': False,
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
        # updatedAt must be *strictly* later than the attempt's transport
        # timestamp for the ABA freshness guard to engage. Odoo Datetime is
        # second-resolution, so a bare now() captured in the same second as
        # transport_at is not strictly greater; derive it from
        # transport_at + 1 minute instead.
        later_than_transport = fields.Datetime.to_string(
            fields.Datetime.add(attempt.transport_at, minutes=1)
        )
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 5.0,
                'updated_at': later_than_transport,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_missing_freshness_never_defaults_to_not_applied(self):
        """No `updatedAt` evidence at all must never be read as proof of
        not-applied -- it must stay inconclusive (PR #182 comment
        5025765389 item 4)."""
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 5.0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_malformed_freshness_timestamp_never_defaults_to_not_applied(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 5.0, 'updated_at': 'not-a-real-timestamp',
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_stale_freshness_evidence_supports_not_applied(self):
        """A same-value read whose updatedAt is *not* later than transport
        is affirmative evidence of no post-transport change -- the only
        case that may yield not_applied."""
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        earlier_than_transport = fields.Datetime.to_string(
            fields.Datetime.now() - timedelta(hours=1)
        )
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 5.0, 'updated_at': earlier_than_transport,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'not_applied')

    def test_applied_verdict_has_no_updated_at_condition(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 10.0,
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

    def test_release_resolves_attempt_by_forward_job_id_not_reconciliation_link(self):
        """Known-P1 reproduction (PR #182 comment 5030781330): an ordinary
        blocked mutation job's own attempt is reachable only through the
        attempt's forward `job_id`, never the reconciliation-job-owned
        `mutation_attempt_id` field (which stays NULL for it). The release
        action must resolve the attempt by `job_id` and release the
        otherwise-eligible pair; the pre-correction code read
        `blocked_job.mutation_attempt_id` (always empty here) and wrongly
        refused the release. This asserts both the invariant and the fix,
        end to end: exactly one ordinal-0 successor, predecessor cancelled
        and atomically linked, and no mutation attempt on the successor
        (no transport during release)."""
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        job.invalidate_recordset()
        # The reconciliation-owned link is unset on an ordinary mutation
        # job; the attempt is discoverable only by its forward job_id.
        self.assertFalse(job.mutation_attempt_id)
        self.assertEqual(
            self.env['shopify.connector.mutation.attempt'].search(
                [('job_id', '=', job.id)]
            ),
            attempt,
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'Location now stocked, please re-check.'
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(job.cancel_reason, 'manual_review_release')
        successor = job.superseded_by_job_id
        self.assertTrue(successor)
        self.assertEqual(successor.job_type, 'inventory_push_sync')
        self.assertEqual(successor.cas_retry_ordinal, 0)
        # Exactly one successor for this pair, and no mutation attempt was
        # created on it (the release is orchestration-only, never transport).
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('res_id', '=', self.binding.id),
                ('res_model', '=', 'shopify.connector.inventory.level.binding'),
                ('job_type', '=', 'inventory_push_sync'),
                ('state', 'not in', ('cancelled', 'failed_final')),
            ]),
            1,
        )
        self.assertFalse(
            self.env['shopify.connector.mutation.attempt'].search_count(
                [('job_id', '=', successor.id)]
            )
        )

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
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
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

    # ------------------------------------------------------------------
    # CAS-exhaustion release requires the structured stale code (PR #182
    # comment 5028910116 item 8)
    # ------------------------------------------------------------------

    def test_release_denied_cas_exhaustion_without_stale_code(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
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

    def test_release_denied_cas_exhaustion_with_different_code(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'ITEM_NOT_STOCKED_AT_LOCATION', 'field': []},
            ]},
        )
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('reason')

    def test_release_evidence_immutable_through_release(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'CAS exhausted.'
        )
        attempt.invalidate_recordset()
        self.assertEqual(
            attempt.remote_evidence_refs['direct']['user_errors'],
            [{'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []}],
        )

    def test_release_reason_no_message_text_routing(self):
        """Eligibility is decided from structured evidence only -- never
        by matching the free-text release reason string."""
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        with self.assertRaises(UserError):
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('CHANGE_FROM_QUANTITY_STALE')

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
    # PII-safe (not just secret-safe) review-reason redaction (PR #182
    # comment 5028910116 item 11)
    # ------------------------------------------------------------------

    def _block_releasable_job(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self._block_job_with(
            job, 'inventory_location_missing', 'inventory_location_missing',
        )
        return job

    def test_release_reason_uses_audit_safe_helper(self):
        self._block_releasable_job()
        with patch.object(
            type(self.binding), '_audit_safe_reason',
            wraps=self.binding._audit_safe_reason,
        ) as wrapped:
            self.binding.with_user(
                self.user_reviewer
            ).action_recheck_inventory_pair('Ordinary release reason.')
        wrapped.assert_called_once()

    def test_release_reason_redacts_email(self):
        self._block_releasable_job()
        logger_name = (
            'odoo.addons.shopify_connector_inventory.models.'
            'shopify_connector_inventory_service'
        )
        with self.assertLogs(logger_name, level='INFO') as captured:
            self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
                'Escalated by ops@example.com after physical count.'
            )
        joined = '\n'.join(captured.output)
        self.assertNotIn('ops@example.com', joined)
        self.assertIn('redacted-email', joined)

    def test_release_reason_redacts_phone(self):
        self._block_releasable_job()
        logger_name = (
            'odoo.addons.shopify_connector_inventory.models.'
            'shopify_connector_inventory_service'
        )
        with self.assertLogs(logger_name, level='INFO') as captured:
            self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
                'Confirmed by phone, call +1 555 123 4567 for details.'
            )
        joined = '\n'.join(captured.output)
        self.assertNotIn('555 123 4567', joined)
        self.assertIn('redacted-phone', joined)

    def test_release_reason_redacts_token(self):
        self._block_releasable_job()
        logger_name = (
            'odoo.addons.shopify_connector_inventory.models.'
            'shopify_connector_inventory_service'
        )
        with self.assertLogs(logger_name, level='INFO') as captured:
            self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
                'Reproduced with token shpat_abcdef0123456789 in the log.'
            )
        joined = '\n'.join(captured.output)
        self.assertNotIn('shpat_abcdef0123456789', joined)

    def test_release_reason_retains_ordinary_text(self):
        self._block_releasable_job()
        logger_name = (
            'odoo.addons.shopify_connector_inventory.models.'
            'shopify_connector_inventory_service'
        )
        with self.assertLogs(logger_name, level='INFO') as captured:
            self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
                'Location now confirmed stocked after physical count.'
            )
        joined = '\n'.join(captured.output)
        self.assertIn(
            'Location now confirmed stocked after physical count', joined,
        )

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

    # error_class-position argument index for each known emitting
    # callable, when passed positionally (no call site in this module
    # uses a keyword for this parameter -- checked explicitly below).
    ERROR_CLASS_POSITIONAL_INDEX = {
        '_block_original_job': 1,               # (job, error_class, subreason, message)
        '_block_pair': 1,                        # (job, error_class, subreason, message)
        '_transition_blocked_manual_review': 0,  # (error_class, subreason, message)
        '_transition_retry_waiting': 2,          # (next_retry_at, retry_count, error_class, message)
        'JobHandlerError': 0,                    # (error_class, message[, technical_detail])
        'InventoryPreC2FailClosedError': 0,      # (error_class, subreason, message)
    }
    # Names legitimately allowed in the error_class position: the nine
    # frozen constants, plus the bare `error_class` pass-through
    # parameter name (`_fail_closed_pre_c2(self, job_id, error_class,
    # subreason, message)` forwards its own caller-supplied value
    # unchanged into `InventoryPreC2FailClosedError`; every call site of
    # `_fail_closed_pre_c2` itself already only ever passes one of the
    # nine constants -- visible directly in the source and separately
    # proven by the pre-C2 fail-closed tests asserting each exact
    # resulting `error_class`). Never a `SUBREASON_*`/
    # `MANUAL_REVIEW_SUBREASON_*` name, never an unknown identifier.
    ALLOWED_ERROR_CLASS_NAMES = frozenset((
        'ERROR_CLASS_VALIDATION', 'ERROR_CLASS_LOCATION_MISSING',
        'ERROR_CLASS_CONCURRENCY', 'ERROR_CLASS_THROTTLE',
        'ERROR_CLASS_TEMPORARY', 'ERROR_CLASS_DATA_SHAPE',
        'ERROR_CLASS_IDEMPOTENCY', 'ERROR_CLASS_NO_STRATEGY',
        'ERROR_CLASS_STORE_IDENTITY', 'error_class',
    ))

    @classmethod
    def _error_class_arg_at_call(cls, call_node):
        """Resolve the exact AST node occupying the error_class argument
        position of `call_node`, or `None` if `call_node` does not
        target a known error_class-emitting callable, or a call target
        this module doesn't recognize. Raises `AssertionError` if the
        parameter was passed by keyword (never done in this module;
        this guard only resolves the positional form)."""
        func = call_node.func
        name = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else None
        )
        index = cls.ERROR_CLASS_POSITIONAL_INDEX.get(name)
        if index is None:
            return None
        for kw in call_node.keywords:
            if kw.arg == 'error_class':
                raise AssertionError(
                    '%s must not pass error_class by keyword; this '
                    'guard only resolves the positional form.' % name
                )
        if len(call_node.args) <= index:
            return None
        return call_node.args[index]

    @classmethod
    def _error_class_arg_is_valid(cls, arg):
        """Whether `arg` (an AST node resolved by
        `_error_class_arg_at_call`) is an accepted error_class value:
        a literal string in the frozen nine-value vocabulary, a `Name`
        referencing one of the nine `ERROR_CLASS_*` constants, or the
        one accepted pass-through shape this module actually uses --
        an already-validated domain exception's own `.error_class`
        attribute (e.g. `exc.error_class`)."""
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value in FIXED_ERROR_CLASS_VOCABULARY
        if isinstance(arg, ast.Name):
            return arg.id in cls.ALLOWED_ERROR_CLASS_NAMES
        if isinstance(arg, ast.Attribute):
            return arg.attr == 'error_class'
        return False

    def test_no_error_class_value_outside_fixed_vocabulary(self):
        """Receiver- and argument-aware guard (PR #182 comment
        5029906989 item 2): the previous guard only scanned every
        string literal anywhere in the file, so it never actually
        inspected what value each call site puts in the error_class
        argument position -- it stayed green even while
        `_ensure_reconciliation_job` passed `SUBREASON_DUPLICATE_RISK`
        (a name that is never one of the nine `ERROR_CLASS_*`
        constants) as `error_class` (item 1). This walks every call
        site of the known error_class-emitting callables and proves the
        resolved argument is always the frozen nine-value vocabulary."""
        source, tree = self._service_source_tree()
        del source
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            arg = self._error_class_arg_at_call(node)
            if arg is None:
                continue
            checked += 1
            self.assertTrue(
                self._error_class_arg_is_valid(arg),
                'Invalid error_class argument at a call site: %r' % (
                    ast.dump(arg),
                ),
            )
        self.assertGreater(
            checked, 20,
            'Expected to inspect a substantial number of error_class '
            'call sites; the guard may not be matching real call '
            'sites at all.',
        )

    def test_error_class_vocabulary_guard_detects_subreason_misuse(self):
        """Proves the guard above is not vacuous: it must actually
        REJECT the exact defect comment 5029906989 item 1 found
        (`SUBREASON_DUPLICATE_RISK` used as `error_class`), reject an
        unrecognized literal, and still ACCEPT `duplicate_risk` when it
        legitimately appears in the subreason position (an argument
        this guard never inspects)."""
        bad_name_snippet = ast.parse(
            "self._block_original_job(\n"
            "    original_job, SUBREASON_DUPLICATE_RISK,\n"
            "    SUBREASON_DUPLICATE_RISK, 'msg',\n"
            ")"
        ).body[0].value
        bad_arg = self._error_class_arg_at_call(bad_name_snippet)
        self.assertIsNotNone(bad_arg)
        self.assertFalse(self._error_class_arg_is_valid(bad_arg))

        unknown_literal_snippet = ast.parse(
            "self._block_pair(job, 'some_unregistered_value', "
            "SUBREASON_BINDING_CONFLICT, 'msg')"
        ).body[0].value
        unknown_arg = self._error_class_arg_at_call(unknown_literal_snippet)
        self.assertIsNotNone(unknown_arg)
        self.assertFalse(self._error_class_arg_is_valid(unknown_arg))

        good_snippet = ast.parse(
            "self._block_original_job(\n"
            "    original_job, ERROR_CLASS_DATA_SHAPE,\n"
            "    SUBREASON_DUPLICATE_RISK, 'msg',\n"
            ")"
        ).body[0].value
        good_arg = self._error_class_arg_at_call(good_snippet)
        self.assertIsNotNone(good_arg)
        self.assertTrue(
            self._error_class_arg_is_valid(good_arg),
            'duplicate_risk in the subreason position (an argument '
            'this guard never inspects) must remain valid.',
        )

    def test_fail_closed_pre_c2_call_sites_use_fixed_vocabulary(self):
        """Closes the one pass-through gap the guard above must accept
        (`_fail_closed_pre_c2`'s own `error_class` parameter): every
        call SITE of `_fail_closed_pre_c2` itself must supply one of
        the nine frozen constants directly, never a `SUBREASON_*` name
        or unknown literal."""
        source, tree = self._service_source_tree()
        del source
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None
            )
            if name != '_fail_closed_pre_c2':
                continue
            if len(node.args) <= 1:
                continue
            arg = node.args[1]
            checked += 1
            self.assertTrue(
                isinstance(arg, ast.Name)
                and arg.id in self.ALLOWED_ERROR_CLASS_NAMES
                and arg.id != 'error_class',
                'Invalid error_class argument at a _fail_closed_pre_c2 '
                'call site: %r' % (ast.dump(arg),),
            )
        self.assertGreater(checked, 5)

    def test_withdrawn_error_class_literals_absent(self):
        source, tree = self._service_source_tree()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(
                    node.value, WITHDRAWN_ERROR_CLASS_VALUES,
                    'Withdrawn error_class literal found: %r' % node.value,
                )

    # ------------------------------------------------------------------
    # Additional static/AST guards for this correction cycle (PR #182
    # comment 5028910116 §19)
    # ------------------------------------------------------------------

    def test_no_synthetic_inventory_level_gid_pattern(self):
        """The synthetic `<item_gid>:<location_gid>` composite identity
        must never be constructed anywhere in the module again -- only
        the real, observed InventoryLevel GID is ever persisted to
        `shopify_gid` (item 2)."""
        source, _tree = self._service_source_tree()
        self.assertNotIn("'%s:%s'", source)

    def test_exact_reconciliation_identity_format_present(self):
        source, _tree = self._service_source_tree()
        self.assertIn("'reconcile:%s:%s:%s' % (", source)

    def test_handoff_supersede_signature_has_no_ordinal_parameter(self):
        """No caller may request an arbitrary CAS ordinal jump -- the
        parameter itself must not exist on `_handoff_supersede` (item
        7)."""
        _source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_handoff_supersede'
        )
        arg_names = {arg.arg for arg in method.args.args + method.args.kwonlyargs}
        self.assertNotIn('cas_retry_ordinal', arg_names)
        self.assertIn('is_cas_replacement', arg_names)

    def test_location_sync_uses_validated_response_helper(self):
        """The location-sync handler must route every page through the
        fail-closed shape validator, never default-empty coercion
        (item 10)."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_handle_inventory_location_sync'
        )
        method_source = ast.get_source_segment(source, method) or ''
        self.assertIn('_validate_locations_response', method_source)
        self.assertNotIn("get('data') or {}", method_source)
        self.assertNotIn("get('locations') or {}", method_source)
        self.assertNotIn("get('edges') or []", method_source)

    def test_apply_consequence_activate_handoff_called_exactly_once(self):
        """Source guard (PR #182 comment 5030514895 item 1): the clean
        activation-success branch of `_apply_consequence_activate` must
        call `_handoff_succeed_to_fresh_orchestration` exactly once --
        the previous defect called it once conditionally and then once
        more unconditionally, creating a duplicate successor on every
        clean success and a spurious one after a GID conflict."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_apply_consequence_activate'
        )
        call_count = 0
        for node in ast.walk(method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == '_handoff_succeed_to_fresh_orchestration'
            ):
                call_count += 1
        self.assertEqual(
            call_count, 1,
            '_apply_consequence_activate must call '
            '_handoff_succeed_to_fresh_orchestration exactly once; found '
            '%d call site(s).' % call_count,
        )

    def test_review_release_uses_audit_safe_reason_not_bare_redact(self):
        """The review-release path must use the PII-safe audit helper,
        never bare secret-only `redact()` (item 11)."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_recheck_inventory_pair'
        )
        method_source = ast.get_source_segment(source, method) or ''
        self.assertIn('_audit_safe_reason', method_source)
        self.assertNotIn('redact(', method_source)

    def test_push_sync_handoffs_acquire_binding_row_lock(self):
        """Both orchestration->mutation handoff branches must acquire
        the binding's row lock before terminalizing (item 12)."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_handle_inventory_push_sync'
        )
        method_source = ast.get_source_segment(source, method) or ''
        self.assertEqual(
            method_source.count('binding.try_lock_for_update()'), 2,
            'Both handoff-A branches must acquire the binding row lock.',
        )

    def test_reconcile_handler_reraises_before_wrapping_generic_exception(self):
        """Exception ordering, specific to general (LL-013, item 9),
        WITHIN `_handle_inventory_mutation_reconcile` itself: the
        `except JobHandlerError: raise` / `except
        PG_CONCURRENCY_EXCEPTIONS_TO_RETRY: raise` branches must appear
        textually before the generic `except Exception` branch that
        wraps a transient read failure."""
        source, tree = self._service_source_tree()
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_handle_inventory_mutation_reconcile'
        )
        method_source = ast.get_source_segment(source, method) or ''
        reraise_index = method_source.index('except JobHandlerError:')
        pg_reraise_index = method_source.index(
            'except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:'
        )
        generic_index = method_source.index(
            "'The reconciliation read failed transiently"
        )
        self.assertLess(reraise_index, generic_index)
        self.assertLess(pg_reraise_index, generic_index)

    def test_no_quantities_array_length_greater_than_one(self):
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 3, 'updated_at': False,
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

    def test_read_query_uses_nested_inventory_item_level(self):
        """The 2026-07 root `inventoryLevel` field no longer accepts
        `inventoryItemId`/`locationId` -- the pair read must always go
        through `inventoryItem(id:) { inventoryLevel(locationId:) }`
        (PR #182 comment 5025765389 item 1)."""
        source, _tree = self._service_source_tree()
        self.assertIn('inventoryItem(id: $itemId)', source)
        self.assertIn('inventoryLevel(locationId: $locationId)', source)
        self.assertNotIn('inventoryLevel(inventoryItemId:', source)

    def test_both_mutations_declare_idempotent_directive(self):
        source, _tree = self._service_source_tree()
        self.assertIn('$idempotencyKey: String!', source)
        self.assertEqual(
            source.count('@idempotent(key: $idempotencyKey)'), 2,
            'Both inventorySetQuantities and inventoryActivate must '
            'declare the @idempotent directive exactly once each.',
        )

    def test_change_from_quantity_present_compare_quantity_absent(self):
        source, _tree = self._service_source_tree()
        self.assertIn('changeFromQuantity', source)
        self.assertNotIn('compareQuantity', source)

    def test_reference_document_uri_uses_database_uuid_not_dbname(self):
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 3, 'updated_at': False,
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
        uri = request['variables']['input']['referenceDocumentUri']
        db_uuid = self.env['ir.config_parameter'].sudo().get_param(
            'database.uuid'
        )
        self.assertEqual(uri, 'odoo://%s/shopify.connector.job/1' % db_uuid)
        self.assertNotIn(self.env.cr.dbname, uri)

    def test_integrality_gate_helper_boundaries(self):
        from odoo.addons.shopify_connector_inventory.models.\
            shopify_connector_inventory_service import (
                _integral_quantity_or_none,
            )
        self.assertEqual(_integral_quantity_or_none(10.0), (10, True))
        self.assertEqual(_integral_quantity_or_none(0.0), (0, True))
        self.assertEqual(_integral_quantity_or_none(9.999999997), (10, True))
        self.assertEqual(_integral_quantity_or_none(10.5), (None, False))

    def _prepare_set_quantities_snapshot(self, job):
        return {
            'job_id': job.id, 'store_id': self.store.id,
            'binding_id': self.binding.id,
            'inventory_item_gid': self.binding.shopify_inventory_item_gid,
            'location_gid': self.mapping.shopify_gid,
            'expected_connection_generation':
                job.expected_connection_generation,
            'expected_store_identity': self.store.shop_domain,
        }

    def test_fractional_target_blocks_before_c2_no_attempt_no_transport(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(self.Service), '_refresh_pending_target',
            return_value=(10.5, 10.5),
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(ctx.exception.subreason, 'binding_conflict')
        job.invalidate_recordset()
        # No domain-side commit (LL-005 / item 3): prepare_preconditions
        # alone never writes to or terminalizes the job.
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_fresh_pre_c2_missing_item_blocks_no_attempt(self):
        """A stale/recreated InventoryItem identity fails closed through
        binding_conflict, never treated as a missing level (PR #182
        comment 5028910116 item 1)."""
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': None, 'item_exists': False, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'shopify_user_errors_validation')
        self.assertEqual(ctx.exception.subreason, 'binding_conflict')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_fresh_pre_c2_level_absence_blocks_no_zero_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'inventory_location_missing')
        self.assertEqual(
            ctx.exception.subreason, 'inventory_location_missing',
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_fresh_pre_c2_untracked_blocks_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': False, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 5, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'inventory_location_missing')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_fresh_pre_c2_store_identity_mismatch_blocks_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/1',
                'available': 5, 'updated_at': False,
                'store_identity': 'a-different-shop.myshopify.com',
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'store_identity_mismatch')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_fresh_pre_c2_conflicting_gid_blocks_no_attempt(self):
        """A fresh pre-C2 read observing an InventoryLevel GID that
        conflicts with the already-recorded one fails closed rather than
        silently overwriting it (PR #182 comment 5028910116 item 2)."""
        self.binding.sudo().write({
            'shopify_gid': 'gid://shopify/InventoryLevel/RECORDED',
        })
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/OBSERVED',
                'available': 5, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_set_quantities(
                    self._prepare_set_quantities_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(ctx.exception.subreason, 'binding_conflict')
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.binding.shopify_gid, 'gid://shopify/InventoryLevel/RECORDED',
        )

    def test_fresh_pre_c2_captures_gid_when_binding_empty(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/CAPTURED',
                'available': 5, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            self.Service._prepare_preconditions_set_quantities(
                self._prepare_set_quantities_snapshot(job), {},
            )
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.binding.shopify_gid, 'gid://shopify/InventoryLevel/CAPTURED',
        )

    # ------------------------------------------------------------------
    # No domain-side commit / durable recovery seam (PR #182 comment
    # 5028910116 item 3)
    # ------------------------------------------------------------------

    def test_no_direct_commit_in_prepare_path_source(self):
        source, tree = self._service_source_tree()
        methods = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        for name in (
            '_fail_closed_pre_c2', '_prepare_preconditions_set_quantities',
            '_prepare_preconditions_activate',
        ):
            method_source = ast.get_source_segment(source, methods[name]) or ''
            self.assertNotIn(
                'self.env.cr.commit', method_source,
                '%s must never directly commit (LL-005).' % name,
            )

    # The genuine independent-connection proof that the recovery seam
    # itself durably commits (mirroring core's own
    # `test_pre_c2_recovery_that_discovers_c2_marks_uncertain`) lives in
    # `TestInventoryPreC2RecoverySeam` below -- a `TransactionCase`'s own
    # uncommitted transaction is never visible to a separate `db_connect`
    # connection, so that proof needs its own durably-committed fixture,
    # not a job created through `self.env` here.

    # ------------------------------------------------------------------
    # Direct-success evidence (never a bare empty userErrors list)
    # ------------------------------------------------------------------

    def test_set_quantities_success_rejects_missing_adjustment_group(self):
        result = {
            'user_errors': [], 'adjustment_group': None,
            'requested_target': 10, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )
        self.assertEqual(consequence['action'], 'reconcile')

    def test_set_quantities_success_rejects_mismatched_quantity_after_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-1',
                'changes': [{
                    'name': 'available', 'delta': 5,
                    'quantityAfterChange': 999,
                }],
            },
            'requested_target': 10, 'requested_reason': 'correction',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(consequence['action'], 'reconcile')

    def test_set_quantities_success_accepts_matching_evidence(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-1',
                'changes': [{
                    'name': 'available', 'delta': 5,
                    'quantityAfterChange': 10,
                }],
            },
            'requested_target': 10, 'requested_reason': 'correction',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'succeeded')
        self.assertEqual(consequence['action'], 'succeed')

    def test_set_quantities_success_rejects_missing_reason_and_uri(self):
        """Two missing values comparing equal (`None == None`) is never
        valid success evidence (PR #182 comment 5029906989 item 8) --
        the false-green fixture bug the two tests above predated and
        left uncovered before this correction cycle."""
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [{'name': 'available', 'quantityAfterChange': 10}],
            },
            'requested_target': 10, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )

    def test_activate_success_rejects_item_location_mismatch(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/1',
                'item': {'id': 'gid://shopify/InventoryItem/WRONG'},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': 0}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )

    def test_activate_success_rejects_nonzero_available(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/1',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': 5}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_activate_success_accepts_matching_evidence(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/1',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': 0}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'succeeded')
        self.assertEqual(consequence['action'], 'succeed')

    # ------------------------------------------------------------------
    # Exact operation_scope_key literal (PR #182 comment 5025765389
    # item 11)
    # ------------------------------------------------------------------

    def test_operation_scope_key_exact_literal_for_pair_jobs(self):
        for job_type in (
            'inventory_push_sync', 'inventory_activate',
            'inventory_set_quantities',
        ):
            job, _token = self._make_mutation_job(job_type)
            self.assertEqual(job.operation_scope_key, self.pair_key)
            job.sudo().write({'state': 'cancelled', 'cancel_reason': 'x'})

    def test_operation_scope_key_not_pair_literal_for_reconciliation(self):
        # A reconciliation job is created through _ensure_reconciliation_job
        # with the exact mutation attempt it reconciles (core's
        # _check_reconciliation_attempt_link constraint requires it); it is
        # never a bare enqueue. Its operation_scope_key keeps core's default
        # composite, never the pair literal used by the three pair-execution
        # job types.
        Dispatch = self.env['shopify.connector.job.dispatch']
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        reconciliation_job = Dispatch._ensure_reconciliation_job(job, attempt)
        self.assertNotEqual(
            reconciliation_job.operation_scope_key, self.pair_key,
        )

    def test_operation_scope_key_retained_while_blocked(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        # Core blocks the job before the domain callback runs (see
        # job_dispatch `_commit`/`_apply` ordering); replicate that seam.
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': 'inventory_location_missing',
            'manual_review_subreason': 'inventory_location_missing',
            'finished_at': fields.Datetime.now(),
        })
        self.Service._apply_consequence_set_quantities(
            job, attempt, 'direct',
            {
                'observed_outcome': 'failed_clean',
                'error_class': 'inventory_location_missing',
                'manual_review_subreason': 'inventory_location_missing',
                'action': 'block_manual_review',
                'message': 'x', 'evidence': {},
            },
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.operation_scope_key, self.pair_key)

    def test_operation_scope_key_cleared_on_succeeded(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        job.invalidate_recordset()
        self.assertFalse(job.operation_scope_key)

    def test_operation_scope_key_cleared_on_cancelled(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        job.sudo().write({'state': 'cancelled', 'cancel_reason': 'test'})
        job.invalidate_recordset()
        self.assertFalse(job.operation_scope_key)

    def test_operation_scope_key_cleared_when_superseded(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        placeholder, _t2 = self._make_mutation_job('inventory_activate')
        placeholder.sudo().write({
            'state': 'cancelled', 'cancel_reason': 'placeholder',
        })
        job.sudo().write({
            'state': 'cancelled', 'cancel_reason': 'superseded',
            'superseded_by_job_id': placeholder.id,
        })
        job.invalidate_recordset()
        self.assertFalse(job.operation_scope_key)

    @mute_logger('odoo.sql_db')
    def test_duplicate_pair_rejected_via_operation_scope_key(self):
        self._make_mutation_job('inventory_push_sync')
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._make_mutation_job('inventory_push_sync')

    def test_different_pair_admitted_despite_first_pair_in_progress(self):
        self._make_mutation_job('inventory_push_sync')
        other_location = self.env['stock.location'].create({
            'name': 'Push Mechanics Other Location',
            'usage': 'internal',
            'location_id': self.warehouse.view_location_id.id,
        })
        other_mapping = self.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Location/501',
            'odoo_location_id': other_location.id,
            'match_key': 'manual',
        })
        other_binding = self.env['shopify.connector.inventory.level.binding'].sudo().create({
            'store_id': self.store.id,
            'product_variant_binding_id': self.variant_binding.id,
            'location_mapping_id': other_mapping.id,
            'shopify_inventory_item_gid': self.binding.shopify_inventory_item_gid,
            'first_push_state': 'confirmed',
        })
        new_job = self.Service._create_inventory_job(
            self.store, 'scheduled_sync', 'inventory_push_sync', other_binding,
        )
        self.assertTrue(new_job)
        self.assertNotEqual(new_job.operation_scope_key, self.pair_key)

    # ------------------------------------------------------------------
    # cas_retry_ordinal protection (PR #182 comment 5025765389 item 12)
    # ------------------------------------------------------------------

    def test_cas_retry_ordinal_denied_on_generic_create(self):
        with self.assertRaises(AccessError):
            self.env['shopify.connector.job'].with_user(
                self.user_operator
            ).create({
                'store_id': self.store.id,
                'job_source': 'scheduled_sync',
                'job_type': 'inventory_set_quantities',
                'state': 'queued',
                'cas_retry_ordinal': 1,
            })

    def test_cas_retry_ordinal_denied_on_generic_write(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        with self.assertRaises(AccessError):
            job.with_user(self.user_reviewer).write({'cas_retry_ordinal': 2})
        with self.assertRaises(AccessError):
            job.with_user(self.user_operator).write({'cas_retry_ordinal': 2})

    def test_cas_retry_ordinal_sudo_write_allowed(self):
        job, _token = self._make_mutation_job('inventory_set_quantities')
        job.sudo().write({'cas_retry_ordinal': 2})
        job.invalidate_recordset()
        self.assertEqual(job.cas_retry_ordinal, 2)

    def test_cas_retry_ordinal_range_enforced(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['shopify.connector.job'].sudo().create({
                    'store_id': self.store.id,
                    'job_source': 'scheduled_sync',
                    'job_type': 'inventory_set_quantities',
                    'state': 'queued',
                    'cas_retry_ordinal': 4,
                })

    def test_cas_retry_ordinal_only_for_set_quantities(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['shopify.connector.job'].sudo().create({
                    'store_id': self.store.id,
                    'job_source': 'scheduled_sync',
                    'job_type': 'inventory_activate',
                    'state': 'queued',
                    'cas_retry_ordinal': 1,
                })

    # ------------------------------------------------------------------
    # Core enqueue-service adoption / coalescing correction (PR #182
    # comment 5025765389 items 9-10)
    # ------------------------------------------------------------------

    def test_ordinary_admission_routes_through_core_enqueue_service(self):
        with patch.object(
            type(self.env['shopify.connector.job.enqueue']), 'enqueue',
            wraps=self.env['shopify.connector.job.enqueue'].enqueue,
        ) as wrapped_enqueue:
            self.Service._create_inventory_job(
                self.store, 'scheduled_sync', 'inventory_push_sync',
                self.binding,
            )
        wrapped_enqueue.assert_called_once()

    def test_try_enqueue_push_sync_propagates_unrelated_validation_error(self):
        with patch.object(
            type(self.env['shopify.connector.job.enqueue']), 'enqueue',
            side_effect=ValidationError('An unrelated configuration error.'),
        ):
            with self.assertRaises(ValidationError):
                self.Service._try_enqueue_push_sync(
                    self.store, self.binding, 'scheduled_sync',
                )

    def test_try_enqueue_push_sync_coalesces_only_exact_scope_collision(self):
        self._make_mutation_job('inventory_push_sync')
        result = self.Service._try_enqueue_push_sync(
            self.store, self.binding, 'scheduled_sync',
        )
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # Typed scan-job cron correction (PR #182 comment 5025765389 item
    # 13)
    # ------------------------------------------------------------------

    def test_cron_enqueues_typed_scan_job_not_inline(self):
        self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', self.store.id),
        ]).write({'inventory_scheduled_sync_enabled': True})
        jobs = self.Service.run_inventory_push_scan()
        self.assertTrue(jobs)
        self.assertTrue(all(j.job_type == 'inventory_push_scan' for j in jobs))
        self.assertTrue(all(j.state == 'queued' for j in jobs))

    def test_scan_handler_enqueues_deltas_for_its_own_store_only(self):
        self.binding.sudo().write({
            'last_pushed_available': 0.0, 'pending_target_available': 0.0,
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })
        with patch.object(
            type(self.Service), '_refresh_pending_target',
            return_value=(7.0, 7.0),
        ):
            self.Service._handle_inventory_push_scan(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        scan_jobs = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertTrue(scan_jobs)

    # ------------------------------------------------------------------
    # Shared reconciliation identity includes store + mutation domain
    # (PR #182 comment 5028910116 item 6)
    # ------------------------------------------------------------------

    def test_shared_reconciliation_identity_includes_store_and_domain(self):
        Dispatch = self.env['shopify.connector.job.dispatch']
        for job_type in ('inventory_set_quantities', 'inventory_activate'):
            job, token = self._make_mutation_job(job_type)
            attempt = self._make_attempt(job, token)
            reconciliation_job = Dispatch._ensure_reconciliation_job(
                job, attempt,
            )
            self.assertEqual(
                reconciliation_job.job_type, 'inventory_mutation_reconcile',
            )
            self.assertEqual(
                reconciliation_job.payload_hash,
                'reconcile:%s:%s:%s' % (self.store.id, job_type, token),
            )
            self.assertEqual(
                reconciliation_job.mutation_attempt_id, attempt,
            )
            # Only one non-terminal pair-execution job may hold the pair's
            # operation_scope_key at a time; terminalize this iteration's
            # mutation job before the next job_type creates its own, exactly
            # as the real serialized lifecycle would.
            job.sudo().write({'state': 'cancelled', 'cancel_reason': 'test'})

    def test_shared_reconciliation_identity_idempotent_on_reuse(self):
        Dispatch = self.env['shopify.connector.job.dispatch']
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        first = Dispatch._ensure_reconciliation_job(job, attempt)
        second = Dispatch._ensure_reconciliation_job(job, attempt)
        self.assertEqual(first.id, second.id)

    # ------------------------------------------------------------------
    # CAS ordinal lineage: no arbitrary jump, no non-CAS inheritance (PR
    # #182 comment 5028910116 item 7)
    # ------------------------------------------------------------------

    def test_handoff_supersede_rejects_arbitrary_ordinal_kwarg(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        self._make_attempt(job, token)
        with self.assertRaises(TypeError):
            self.Service._handoff_supersede(
                job, self.binding, 'cas_stale_bounded_replacement',
                'inventory_set_quantities', cas_retry_ordinal=2,
            )

    def test_cas_replacement_ordinal_always_derived_predecessor_plus_one(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=1,
        )
        attempt = self._make_attempt(job, token)
        # `_create_cas_successor_job` independently re-verifies the frozen
        # stale-CAS evidence (failed_clean/not_applied + structured
        # CHANGE_FROM_QUANTITY_STALE) before deriving the ordinal; the
        # predecessor must carry it.
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
        new_job = self.Service._handoff_supersede(
            job, self.binding, 'cas_stale_bounded_replacement',
            'inventory_set_quantities', is_cas_replacement=True,
        )
        self.assertEqual(new_job.cas_retry_ordinal, 2)

    def test_cas_replacement_denied_at_or_above_ceiling(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        self._make_attempt(job, token)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._handoff_supersede(
                    job, self.binding, 'cas_stale_bounded_replacement',
                    'inventory_set_quantities', is_cas_replacement=True,
                )

    def test_cas_replacement_denied_for_non_set_quantities_job_type(self):
        job, token = self._make_mutation_job('inventory_activate')
        self._make_attempt(job, token)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._handoff_supersede(
                    job, self.binding, 'cas_stale_bounded_replacement',
                    'inventory_activate', is_cas_replacement=True,
                )

    def test_ordinary_admission_never_sets_nonzero_cas_ordinal(self):
        job = self.Service._create_inventory_job(
            self.store, 'scheduled_sync', 'inventory_set_quantities',
            self.binding,
        )
        self.assertEqual(job.cas_retry_ordinal, 0)

    def test_reconciliation_replacement_never_inherits_cas_ordinal(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=2,
        )
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
        self.assertEqual(job.superseded_by_job_id.cas_retry_ordinal, 0)

    def test_manual_review_release_replacement_ordinal_zero(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
        self._block_job_with(
            job, 'concurrency_race_conflict', 'binding_conflict',
        )
        self.binding.with_user(self.user_reviewer).action_recheck_inventory_pair(
            'CAS exhausted, releasing.'
        )
        job.invalidate_recordset()
        self.assertEqual(job.superseded_by_job_id.cas_retry_ordinal, 0)

    # ------------------------------------------------------------------
    # Strict integer evidence / ambiguous data+errors / exact-request
    # matching (PR #182 comment 5028910116 item 4)
    # ------------------------------------------------------------------

    def test_set_quantities_success_rejects_bool_quantity_after_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [{'name': 'available', 'quantityAfterChange': True}],
            },
            'requested_target': 1, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_float_quantity_after_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [{'name': 'available', 'quantityAfterChange': 10.0}],
            },
            'requested_target': 10, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_string_quantity_after_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [{'name': 'available', 'quantityAfterChange': '10'}],
            },
            'requested_target': 10, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_duplicate_available_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [
                    {'name': 'available', 'quantityAfterChange': 10},
                    {'name': 'available', 'quantityAfterChange': 10},
                ],
            },
            'requested_target': 10, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_extra_quantity_name_change(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': None, 'referenceDocumentUri': None,
                'changes': [
                    {'name': 'available', 'quantityAfterChange': 10},
                    {'name': 'on_hand', 'quantityAfterChange': 10},
                ],
            },
            'requested_target': 10, 'requested_reason': None,
            'requested_reference_uri': None, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_reason_mismatch(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-1',
                'changes': [{'name': 'available', 'quantityAfterChange': 10}],
            },
            'requested_target': 10, 'requested_reason': 'a_different_reason',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_rejects_reference_uri_mismatch(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-wrong',
                'changes': [{'name': 'available', 'quantityAfterChange': 10}],
            },
            'requested_target': 10, 'requested_reason': 'correction',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_set_quantities_success_accepts_exact_matching_evidence(self):
        result = {
            'user_errors': [],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-1',
                'changes': [{'name': 'available', 'quantityAfterChange': 10}],
            },
            'requested_target': 10, 'requested_reason': 'correction',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'succeeded')
        self.assertEqual(consequence['evidence']['quantity_after_change'], 10)
        self.assertEqual(consequence['evidence']['reason'], 'correction')

    def test_set_quantities_data_plus_errors_is_ambiguous_not_clean_rejection(self):
        result = {
            'user_errors': [{'code': 'SOME_ERROR', 'field': [], 'message': 'x'}],
            'adjustment_group': {
                'reason': 'correction', 'referenceDocumentUri': 'uri-1',
                'changes': [{'name': 'available', 'quantityAfterChange': 10}],
            },
            'requested_target': 10, 'requested_reason': 'correction',
            'requested_reference_uri': 'uri-1', 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )
        self.assertEqual(consequence['action'], 'reconcile')

    def test_activate_success_rejects_bool_available(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/1',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': False}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_activate_success_rejects_missing_level_gid(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': '',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': 0}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_activate_success_rejects_duplicate_quantity_entries(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/1',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [
                    {'name': 'available', 'quantity': 0},
                    {'name': 'available', 'quantity': 0},
                ],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_activate_success_captures_inventory_level_gid_evidence(self):
        result = {
            'user_errors': [],
            'inventory_level': {
                'id': 'gid://shopify/InventoryLevel/999',
                'item': {'id': self.binding.shopify_inventory_item_gid},
                'location': {'id': self.mapping.shopify_gid},
                'quantities': [{'name': 'available', 'quantity': 0}],
            },
            'requested_item_gid': self.binding.shopify_inventory_item_gid,
            'requested_location_gid': self.mapping.shopify_gid,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'succeeded')
        self.assertEqual(
            consequence['evidence']['inventory_level_gid'],
            'gid://shopify/InventoryLevel/999',
        )

    # ------------------------------------------------------------------
    # Real InventoryLevel GID persistence, never a synthetic identity
    # (PR #182 comment 5028910116 item 2)
    # ------------------------------------------------------------------

    def test_activate_success_persists_real_gid_never_synthetic(self):
        job, token = self._make_mutation_job('inventory_activate')
        attempt = self._make_attempt(job, token)
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        self.Service._apply_consequence_activate(
            job, attempt, 'direct',
            {
                'observed_outcome': 'succeeded', 'error_class': False,
                'manual_review_subreason': False, 'action': 'succeed',
                'message': 'Activated.',
                'evidence': {
                    'inventory_level_gid': 'gid://shopify/InventoryLevel/777',
                },
            },
        )
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.binding.shopify_gid, 'gid://shopify/InventoryLevel/777',
        )
        self.assertNotIn(':', self.binding.shopify_gid.replace('gid://shopify/InventoryLevel/', ''))
        # No conflict was flagged, so the ordinary fresh-orchestration
        # handoff (Handoff B) fires exactly once -- never twice (PR #182
        # comment 5030514895 item 1: the duplicate unconditional call
        # that followed the conditional one used to create a second
        # successor here).
        successors = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertEqual(len(successors), 1)
        # The handoff itself only enqueues a job; it never creates a
        # mutation attempt (attempts are created exclusively at a later
        # job's own C2 time).
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', 'in', successors.ids),
        ]))

    @mute_logger(
        'odoo.addons.shopify_connector_inventory.models.'
        'shopify_connector_inventory_service'
    )
    def test_activate_success_conflicting_gid_flags_review_not_overwrite(self):
        self.binding.sudo().write({
            'shopify_gid': 'gid://shopify/InventoryLevel/RECORDED',
        })
        job, token = self._make_mutation_job('inventory_activate')
        attempt = self._make_attempt(job, token)
        job.sudo().write({'state': 'succeeded', 'finished_at': fields.Datetime.now()})
        self.Service._apply_consequence_activate(
            job, attempt, 'direct',
            {
                'observed_outcome': 'succeeded', 'error_class': False,
                'manual_review_subreason': False, 'action': 'succeed',
                'message': 'Activated.',
                'evidence': {
                    'inventory_level_gid': 'gid://shopify/InventoryLevel/DIFFERENT',
                },
            },
        )
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.binding.shopify_gid, 'gid://shopify/InventoryLevel/RECORDED',
        )
        self.assertEqual(self.binding.status, 'review')
        # A post-mutation GID conflict must create zero successors (PR
        # #182 comment 5029906989 item 4 / comment 5030514895 item 1) --
        # the fresh-orchestration handoff is never issued when this
        # outcome flagged the binding for review, and the previously
        # unconditional duplicate call must not have fired either.
        successors = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertEqual(len(successors), 0)

    def test_reconcile_set_quantities_applied_captures_real_gid(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/888',
                'available': 10, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'applied')
        self.assertEqual(
            result['evidence']['inventory_level_gid'],
            'gid://shopify/InventoryLevel/888',
        )

    def test_reconcile_set_quantities_absent_level_routes_location_missing(self):
        """A set-quantities effect cannot be applied to a nonexistent
        InventoryLevel (PR #182 comment 5029906989 item 9): previously
        fell through to a generic `current=None` comparison and
        returned `inconclusive`, consuming the bounded inconclusive-
        retry budget forever instead of routing fail closed."""
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(
            job, token, target_quantity=10.0, change_from_quantity=5.0,
        )
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertNotEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['verdict'], 'not_applied')
        self.assertEqual(result['action'], 'block_manual_review')
        self.assertEqual(result['error_class'], 'inventory_location_missing')
        self.assertEqual(
            result['manual_review_subreason'], 'inventory_location_missing',
        )

    # ------------------------------------------------------------------
    # Missing InventoryItem is never treated as an absent InventoryLevel
    # (PR #182 comment 5028910116 item 1) -- reconciliation paths
    # ------------------------------------------------------------------

    def test_reconcile_set_quantities_missing_item_blocks_manual_review(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': None, 'item_exists': False, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_set_quantities(attempt)
        self.assertEqual(result['verdict'], 'not_applied')
        self.assertEqual(result['action'], 'block_manual_review')
        self.assertEqual(result['manual_review_subreason'], 'binding_conflict')

    def test_reconcile_activate_missing_item_blocks_manual_review(self):
        job, token = self._make_mutation_job('inventory_activate')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('uncertain')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': None, 'item_exists': False, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            result = self.Service._reconcile_activate(attempt)
        self.assertEqual(result['verdict'], 'not_applied')
        self.assertEqual(result['action'], 'block_manual_review')
        self.assertEqual(result['manual_review_subreason'], 'binding_conflict')

    # ------------------------------------------------------------------
    # Reconciliation exception ordering, specific to general (LL-013; PR
    # #182 comment 5028910116 item 9)
    # ------------------------------------------------------------------

    def test_reconcile_handler_reraises_job_handler_error_from_read(self):
        from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
            JobHandlerError as CoreJobHandlerError,
        )
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('uncertain')
        reconciliation_job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'inventory_mutation_reconcile',
            'state': 'running',
            'mutation_attempt_id': attempt.id,
            'payload_hash': 'reconcile:%s:%s:%s' % (
                self.store.id, job.job_type, token,
            ),
            'expected_connection_generation': attempt.expected_connection_generation,
        })
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            side_effect=CoreJobHandlerError(
                'shopify_temporary_server_network', 'transient read error',
            ),
        ):
            with self.assertRaises(CoreJobHandlerError):
                self.Service._handle_inventory_mutation_reconcile(
                    reconciliation_job
                )
        original = self.env['shopify.connector.job'].browse(job.id)
        original.invalidate_recordset()
        # A transient read error must never falsely block the original
        # job -- it stays exactly as it was, awaiting retry.
        self.assertNotEqual(original.state, 'blocked_manual_review')

    def test_reconcile_handler_blocks_on_malformed_result_shape(self):
        job, token = self._make_mutation_job('inventory_set_quantities')
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('uncertain')
        reconciliation_job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'inventory_mutation_reconcile',
            'state': 'running',
            'mutation_attempt_id': attempt.id,
            'payload_hash': 'reconcile:%s:%s:%s' % (
                self.store.id, job.job_type, token,
            ),
            'expected_connection_generation': attempt.expected_connection_generation,
        })
        with patch.object(
            type(self.Service), '_reconcile_set_quantities',
            return_value={'not': 'a valid reconciliation result shape'},
        ):
            self.Service._handle_inventory_mutation_reconcile(reconciliation_job)
        original = self.env['shopify.connector.job'].browse(job.id)
        original.invalidate_recordset()
        self.assertEqual(original.state, 'blocked_manual_review')
        self.assertEqual(original.error_class, 'data_shape_schema_mismatch')

    # ------------------------------------------------------------------
    # Activation fresh pre-C2 read (PR #182 comment 5029906989 item 3)
    # ------------------------------------------------------------------

    def _activate_snapshot(self, job):
        return {
            'job_id': job.id, 'store_id': self.store.id,
            'binding_id': self.binding.id,
            'inventory_item_gid': self.binding.shopify_inventory_item_gid,
            'location_gid': self.mapping.shopify_gid,
            'expected_connection_generation':
                job.expected_connection_generation,
            'expected_store_identity': self.store.shop_domain,
        }

    def test_activate_pre_c2_missing_item_blocks_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_activate')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': None, 'item_exists': False, 'level_exists': False,
                'inventory_level_gid': None, 'available': None,
                'updated_at': False, 'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_activate(
                    self._activate_snapshot(job), {},
                )
        self.assertEqual(
            ctx.exception.error_class, 'shopify_user_errors_validation',
        )
        self.assertEqual(ctx.exception.subreason, 'binding_conflict')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    def test_activate_pre_c2_untracked_blocks_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_activate')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': False, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None, 'available': None,
                'updated_at': False, 'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_activate(
                    self._activate_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'inventory_location_missing')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')

    def test_activate_pre_c2_store_identity_mismatch_blocks_no_attempt(self):
        job, _token = self._make_mutation_job('inventory_activate')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None, 'available': None,
                'updated_at': False,
                'store_identity': 'a-different-shop.myshopify.com',
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_activate(
                    self._activate_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'store_identity_mismatch')

    def test_activate_pre_c2_conflicting_gid_blocks_no_attempt(self):
        self.binding.sudo().write({
            'shopify_gid': 'gid://shopify/InventoryLevel/RECORDED',
        })
        job, _token = self._make_mutation_job('inventory_activate')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/OBSERVED',
                'available': 0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryPreC2FailClosedError) as ctx:
                self.Service._prepare_preconditions_activate(
                    self._activate_snapshot(job), {},
                )
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(ctx.exception.subreason, 'binding_conflict')

    def test_activate_pre_c2_level_already_exists_raises_superseded(self):
        """When a valid InventoryLevel already exists, no activation
        mutation may be sent -- the domain recovery seam (tested
        separately via genuine independent connections below) is
        signalled instead of raising the generic fail-closed error."""
        job, _token = self._make_mutation_job('inventory_activate')
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/999',
                'available': 3, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            with self.assertRaises(InventoryActivationSupersededError) as ctx:
                self.Service._prepare_preconditions_activate(
                    self._activate_snapshot(job), {},
                )
        self.assertEqual(
            ctx.exception.observed_level_gid,
            'gid://shopify/InventoryLevel/999',
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', job.id),
        ]))

    # ------------------------------------------------------------------
    # `review`/`stale` admission gate (PR #182 comment 5029906989 item
    # 4/§10) -- refused across every admission surface; `active` remains
    # eligible.
    # ------------------------------------------------------------------

    def test_review_binding_refused_by_stock_move_admission(self):
        self.binding.sudo().write({'status': 'review'})
        result = self.Service._try_enqueue_push_sync(
            self.store, self.binding, 'odoo_event',
        )
        self.assertFalse(result)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ]))

    def test_stale_binding_refused_by_manual_push(self):
        self.binding.sudo().write({'status': 'stale'})
        enqueued = self.Service._enqueue_manual_push(self.store)
        self.assertFalse(enqueued)

    def test_review_binding_refused_by_scheduled_scan(self):
        self.binding.sudo().write({
            'status': 'review', 'last_pushed_available': 0.0,
            'pending_target_available': 5.0,
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })
        self.Service._handle_inventory_push_scan(job)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ]))

    def test_review_binding_refused_by_direct_orchestration_dispatch(self):
        self.binding.sudo().write({'status': 'review'})
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            # core requires a trigger_origin for every odoo_event job.
            'trigger_origin': 'inventory_stock_change',
            'job_type': 'inventory_push_sync',
            'state': 'running',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': self.binding.id,
            'shopify_target_gid': self.pair_key,
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': self.store.connection_generation,
        })
        self.Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'binding_conflict')

    def test_review_binding_refused_by_cas_replacement_admission(self):
        self.binding.sudo().write({'status': 'review'})
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=1,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome('failed_clean')
        self.Service._apply_consequence_set_quantities(
            job, attempt, 'direct',
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
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(job.superseded_by_job_id)

    def test_review_binding_refused_by_reconciliation_replacement_admission(self):
        self.binding.sudo().write({'status': 'review'})
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
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(job.superseded_by_job_id)

    def test_active_binding_remains_eligible_for_admission(self):
        self.assertEqual(self.binding.status, 'active')
        result = self.Service._try_enqueue_push_sync(
            self.store, self.binding, 'manual_sync',
        )
        self.assertTrue(result)

    def test_review_flagged_after_unlocked_check_blocks_before_child_creation(self):
        """Closes a narrow TOCTOU race (PR #182 comment 5029906989 item
        4): a concurrent writer flagging the binding `review` between
        the orchestration handler's initial unlocked gate check and the
        handoff's own row lock must still be caught -- re-checked under
        the lock, before the child is created."""
        job = self._make_push_sync_dispatch_job()
        original_lock = type(self.binding).try_lock_for_update

        def _flip_to_review_then_lock(recordset):
            locked = original_lock(recordset)
            if locked:
                locked.sudo().write({'status': 'review'})
            return locked

        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None, 'available': None,
                'updated_at': False, 'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(self.binding), 'try_lock_for_update',
            _flip_to_review_then_lock,
        ):
            self.Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_activate'),
            ('res_id', '=', self.binding.id),
        ]))

    # ------------------------------------------------------------------
    # Real InventoryLevel GID persistence in orchestration, before any
    # no-op/child-admission decision (PR #182 comment 5029906989 item 4)
    # ------------------------------------------------------------------

    def _make_push_sync_dispatch_job(self):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            # core requires a trigger_origin for every odoo_event job.
            'trigger_origin': 'inventory_stock_change',
            'job_type': 'inventory_push_sync',
            'state': 'running',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': self.binding.id,
            'shopify_target_gid': self.pair_key,
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': self.store.connection_generation,
        })

    def test_push_sync_captures_gid_when_binding_empty_on_noop(self):
        job = self._make_push_sync_dispatch_job()
        self.binding.sudo().write({'pending_target_available': 10.0})
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/NOOP',
                'available': 10, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            self.Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(
            self.binding.shopify_gid, 'gid://shopify/InventoryLevel/NOOP',
        )

    def test_push_sync_conflicting_gid_blocks_before_child_creation(self):
        self.binding.sudo().write({
            'shopify_gid': 'gid://shopify/InventoryLevel/RECORDED',
            'pending_target_available': 20.0,
        })
        job = self._make_push_sync_dispatch_job()
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/OBSERVED',
                'available': 5, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            self.Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.error_class, 'data_shape_schema_mismatch')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_set_quantities'),
            ('res_id', '=', self.binding.id),
        ]))

    # ------------------------------------------------------------------
    # Verified no-op baseline -- prevents an endless scheduled-read loop
    # (PR #182 comment 5029906989 item 5)
    # ------------------------------------------------------------------

    def test_verified_noop_baseline_prevents_endless_rescan(self):
        self.binding.sudo().write({'pending_target_available': 10.0})
        self.assertFalse(self.binding.last_pushed_at)
        scan_job_1 = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })
        with patch.object(
            type(self.Service), '_refresh_pending_target',
            return_value=(10.0, 10.0),
        ):
            self.Service._handle_inventory_push_scan(scan_job_1)
        first_sync_job = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertEqual(len(first_sync_job), 1)
        first_sync_job.sudo().write({
            'state': 'running', 'current_attempt_token': uuid.uuid4().hex,
        })
        with patch.object(
            type(self.Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'inventory_level_gid': 'gid://shopify/InventoryLevel/BASELINE',
                'available': 10, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            # The orchestration handler always recomputes the target from
            # live Odoo free_qty (last-value-wins); pin it to the intended
            # baseline of 10 so this exercises the verified-noop path (the
            # unstocked fixture product would otherwise derive target=0).
            type(self.Service), '_refresh_pending_target',
            return_value=(10.0, 10.0),
        ):
            self.Service._handle_inventory_push_sync(first_sync_job)
        first_sync_job.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(first_sync_job.state, 'succeeded')
        self.assertTrue(self.binding.last_pushed_at)
        self.assertEqual(self.binding.last_pushed_available, 10.0)
        self.assertFalse(self.env['shopify.connector.mutation.attempt'].search([
            ('job_id', '=', first_sync_job.id),
        ]))

        # Second scan: unchanged target, now-populated last_pushed_at ->
        # must skip, never re-enqueue.
        scan_job_2 = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })
        with patch.object(
            type(self.Service), '_refresh_pending_target',
            return_value=(10.0, 10.0),
        ):
            self.Service._handle_inventory_push_scan(scan_job_2)
        second_pass_sync_jobs = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertEqual(len(second_pass_sync_jobs), 1)
        self.assertEqual(second_pass_sync_jobs.id, first_sync_job.id)

    # ------------------------------------------------------------------
    # CAS ordinal creation surface -- no generic helper can produce a
    # nonzero ordinal (PR #182 comment 5029906989 item 6)
    # ------------------------------------------------------------------

    def test_create_inventory_job_rejects_cas_ordinal_kwarg(self):
        with self.assertRaises(TypeError):
            self.Service._create_inventory_job(
                self.store, 'scheduled_sync', 'inventory_set_quantities',
                self.binding, cas_retry_ordinal=2,
            )

    def test_create_cas_successor_job_requires_set_quantities_job_type(self):
        job, _token = self._make_mutation_job('inventory_activate')
        locked = job.try_lock_for_update()
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_at_ceiling(self):
        job, _token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=3,
        )
        locked = job.try_lock_for_update()
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    # ------------------------------------------------------------------
    # `_create_cas_successor_job` must independently re-verify the
    # immutable stale-CAS evidence itself, never trust the caller (PR
    # #182 comment 5030514895 item 3).
    # ------------------------------------------------------------------

    def _make_stale_cas_predecessor(self, cas_retry_ordinal=1, evidence=None):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=cas_retry_ordinal,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={
                'user_errors': [
                    {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
                ],
            } if evidence is None else evidence,
        )
        # `mutation_attempt_id` is a reconciliation-job-owned field and
        # must never be written on the ordinary predecessor job itself
        # (core's `_check_reconciliation_attempt_link` constraint
        # forbids it) -- the attempt is found by its own `job_id`
        # reference instead, exactly as `_create_cas_successor_job`
        # does.
        return job.try_lock_for_update()

    def test_create_cas_successor_job_derives_ordinal_from_locked_predecessor(self):
        locked = self._make_stale_cas_predecessor(cas_retry_ordinal=1)
        new_job = self.Service._create_cas_successor_job(locked, self.binding)
        self.assertEqual(new_job.cas_retry_ordinal, 2)
        self.assertEqual(new_job.job_type, 'inventory_set_quantities')

    def test_create_cas_successor_job_denies_without_any_attempt(self):
        job, _token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=1,
        )
        locked = job.try_lock_for_update()
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_non_failed_clean_outcome(self):
        job, token = self._make_mutation_job(
            'inventory_set_quantities', cas_retry_ordinal=1,
        )
        attempt = self._make_attempt(job, token)
        attempt._record_direct_outcome(
            'uncertain',
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
            ]},
        )
        locked = job.try_lock_for_update()
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_missing_user_errors_evidence(self):
        locked = self._make_stale_cas_predecessor(
            cas_retry_ordinal=1, evidence={},
        )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_non_list_user_errors_evidence(self):
        locked = self._make_stale_cas_predecessor(
            cas_retry_ordinal=1, evidence={'user_errors': 'not-a-list'},
        )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_non_dict_entry_in_evidence(self):
        locked = self._make_stale_cas_predecessor(
            cas_retry_ordinal=1,
            evidence={'user_errors': ['CHANGE_FROM_QUANTITY_STALE']},
        )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_wrong_code(self):
        locked = self._make_stale_cas_predecessor(
            cas_retry_ordinal=1,
            evidence={'user_errors': [
                {'code': 'ITEM_NOT_STOCKED_AT_LOCATION', 'field': []},
            ]},
        )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    def test_create_cas_successor_job_denies_substring_code_match(self):
        """No substring or generic-container membership is used -- a
        code merely containing the stale marker as a substring is not
        an exact structured entry."""
        locked = self._make_stale_cas_predecessor(
            cas_retry_ordinal=1,
            evidence={'user_errors': [
                {'code': 'CHANGE_FROM_QUANTITY_STALE_VARIANT', 'field': []},
            ]},
        )
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                self.Service._create_cas_successor_job(locked, self.binding)

    # ------------------------------------------------------------------
    # Structured user-error evidence shape (PR #182 comment 5029906989
    # item 7) -- malformed entries are ambiguous, never a clean
    # rejection.
    # ------------------------------------------------------------------

    def test_set_quantities_malformed_user_error_entry_is_ambiguous(self):
        result = {
            'user_errors': [{'field': [], 'message': 'x'}],
            'adjustment_group': None,
            'requested_target': 10, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )

    def test_set_quantities_user_errors_not_a_list_is_ambiguous(self):
        result = {
            'user_errors': 'not-a-list',
            'adjustment_group': None,
            'requested_target': 10, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')

    def test_activate_malformed_user_error_entry_is_ambiguous(self):
        result = {
            'user_errors': ['not-a-dict'],
            'inventory_level': None,
            'evidence': {},
        }
        consequence = self.Service._classify_direct_activate(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )

    def test_set_quantities_non_string_field_entry_is_ambiguous(self):
        """Adversarial case: a `field` list containing non-string parts
        must also fail the strict structured-shape validation, not just
        a missing `code`."""
        result = {
            'user_errors': [{'code': 'SOME_CODE', 'field': [123, None]}],
            'adjustment_group': None,
            'requested_target': 10, 'evidence': {},
        }
        consequence = self.Service._classify_direct_set_quantities(result)
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(
            consequence['error_class'], 'data_shape_schema_mismatch',
        )

    # ------------------------------------------------------------------
    # Strict userErrors container validation (PR #182 comment
    # 5030514895 item 2): `payload.get('userErrors') or []` /
    # `result.get('user_errors') or []` silently turned a malformed
    # falsey container (`{}`, `''`, `0`, `False`, `None`, a tuple) into
    # an apparently valid empty list -- the container's shape must be
    # validated before its emptiness is ever checked.
    # ------------------------------------------------------------------

    MALFORMED_FALSEY_USER_ERROR_CONTAINERS = (None, {}, '', 0, False, ())

    def test_set_quantities_malformed_falsey_user_errors_container_is_ambiguous(self):
        for malformed in self.MALFORMED_FALSEY_USER_ERROR_CONTAINERS:
            with self.subTest(malformed=repr(malformed)):
                result = {
                    'user_errors': malformed,
                    'adjustment_group': None,
                    'requested_target': 10, 'evidence': {},
                }
                consequence = self.Service._classify_direct_set_quantities(
                    result
                )
                self.assertEqual(
                    consequence['observed_outcome'], 'uncertain',
                )
                self.assertEqual(
                    consequence['error_class'],
                    'data_shape_schema_mismatch',
                )

    def test_activate_malformed_falsey_user_errors_container_is_ambiguous(self):
        for malformed in self.MALFORMED_FALSEY_USER_ERROR_CONTAINERS:
            with self.subTest(malformed=repr(malformed)):
                result = {
                    'user_errors': malformed,
                    'inventory_level': None,
                    'evidence': {},
                }
                consequence = self.Service._classify_direct_activate(result)
                self.assertEqual(
                    consequence['observed_outcome'], 'uncertain',
                )
                self.assertEqual(
                    consequence['error_class'],
                    'data_shape_schema_mismatch',
                )

    def test_set_quantities_valid_payload_with_malformed_user_errors_stays_uncertain(self):
        """The exact P0 defect (PR #182 comment 5030514895 item 2): a
        malformed falsey `userErrors` container alongside an otherwise
        fully valid success payload must never be coerced into `[]`
        and trusted as a clean success -- it must never reach
        `_is_valid_set_quantities_success` at all."""
        for malformed in ({}, '', 0, False):
            with self.subTest(malformed=repr(malformed)):
                result = {
                    'user_errors': malformed,
                    'adjustment_group': {
                        'reason': 'correction',
                        'referenceDocumentUri': 'uri-1',
                        'changes': [{
                            'name': 'available', 'delta': 5,
                            'quantityAfterChange': 10,
                        }],
                    },
                    'requested_target': 10, 'requested_reason': 'correction',
                    'requested_reference_uri': 'uri-1', 'evidence': {},
                }
                consequence = self.Service._classify_direct_set_quantities(
                    result
                )
                self.assertEqual(
                    consequence['observed_outcome'], 'uncertain',
                )
                self.assertNotEqual(consequence['action'], 'succeed')

    def test_activate_valid_payload_with_malformed_user_errors_stays_uncertain(self):
        """The exact P0 defect (PR #182 comment 5030514895 item 2),
        activation domain: a malformed falsey `userErrors` container
        alongside an otherwise fully valid `InventoryLevel` success
        payload must never be coerced into `[]` and trusted as a clean
        success."""
        for malformed in ({}, '', 0, False):
            with self.subTest(malformed=repr(malformed)):
                result = {
                    'user_errors': malformed,
                    'inventory_level': {
                        'id': 'gid://shopify/InventoryLevel/999',
                        'item': {'id': self.binding.shopify_inventory_item_gid},
                        'location': {'id': self.mapping.shopify_gid},
                        'quantities': [{'name': 'available', 'quantity': 0}],
                    },
                    'requested_item_gid': self.binding.shopify_inventory_item_gid,
                    'requested_location_gid': self.mapping.shopify_gid,
                    'evidence': {},
                }
                consequence = self.Service._classify_direct_activate(result)
                self.assertEqual(
                    consequence['observed_outcome'], 'uncertain',
                )
                self.assertNotEqual(consequence['action'], 'succeed')

    def test_transport_source_never_defaults_user_errors_container_to_empty_list(self):
        """Source guard (task §8): neither transport adapter may use
        `payload.get('userErrors') or []`, and neither classifier may
        use `result.get('user_errors') or []` -- either pattern
        silently manufactures an empty list out of a malformed falsey
        container before its shape is ever validated."""
        source, tree = self._service_source_tree()
        del tree
        self.assertNotIn("payload.get('userErrors') or []", source)
        self.assertNotIn("result.get('user_errors') or []", source)
        self.assertNotIn('payload.get("userErrors") or []', source)
        self.assertNotIn('result.get("user_errors") or []', source)

    def test_business_reads_use_only_the_job_bound_read_seam(self):
        _source, tree = self._service_source_tree()
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        ]
        self.assertFalse(
            [
                node.lineno for node in calls
                if node.func.attr == 'execute'
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == 'client'
            ],
        )
        read_calls = [
            node for node in calls
            if node.func.attr == 'execute_business_read'
        ]
        self.assertEqual(len(read_calls), 2)
        for call in read_calls:
            purpose = next(
                (kw.value for kw in call.keywords if kw.arg == 'purpose'),
                None,
            )
            self.assertIsInstance(purpose, ast.Constant)
            self.assertEqual(purpose.value, 'inventory')

    # ------------------------------------------------------------------
    # `_read_shopify_inventory_pair` response-shape hardening (PR #182
    # comment 5029906989 item 4/8) -- exercised through a mocked
    # transport, never through mocking the method itself, so the real
    # validation logic runs.
    # ------------------------------------------------------------------

    def _pair_read_response(self, quantities, item_id=None, location_id=None):
        return {'data': {
            'inventoryItem': {
                'id': item_id or self.binding.shopify_inventory_item_gid,
                'tracked': True,
                'inventoryLevel': {
                    'id': 'gid://shopify/InventoryLevel/1',
                    'item': {
                        'id': item_id or self.binding.shopify_inventory_item_gid,
                    },
                    'location': {
                        'id': location_id or self.mapping.shopify_gid,
                    },
                    'quantities': quantities,
                },
            },
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}

    def test_read_pair_rejects_duplicate_available_entries(self):
        with self.assertRaises(JobHandlerError):
            self.Service._inventory_pair_read_result(
                self._pair_read_response([
                    {'name': 'available', 'quantity': 5, 'updatedAt': None},
                    {'name': 'available', 'quantity': 7, 'updatedAt': None},
                ]),
                self.binding.shopify_inventory_item_gid,
                self.mapping.shopify_gid,
            )

    def test_read_pair_rejects_item_identity_mismatch(self):
        with self.assertRaises(JobHandlerError):
            self.Service._inventory_pair_read_result(
                self._pair_read_response(
                    [{'name': 'available', 'quantity': 5, 'updatedAt': None}],
                    item_id='gid://shopify/InventoryItem/DIFFERENT',
                ),
                self.binding.shopify_inventory_item_gid,
                self.mapping.shopify_gid,
            )

    def test_read_pair_rejects_level_location_identity_mismatch(self):
        with self.assertRaises(JobHandlerError):
            self.Service._inventory_pair_read_result(
                self._pair_read_response(
                    [{'name': 'available', 'quantity': 5, 'updatedAt': None}],
                    location_id='gid://shopify/Location/WRONG',
                ),
                self.binding.shopify_inventory_item_gid,
                self.mapping.shopify_gid,
            )

    def test_read_pair_accepts_well_formed_response(self):
        read = self.Service._inventory_pair_read_result(
            self._pair_read_response(
                [{'name': 'available', 'quantity': 5, 'updatedAt': None}],
            ),
            self.binding.shopify_inventory_item_gid,
            self.mapping.shopify_gid,
        )
        self.assertEqual(read['available'], 5)
        self.assertEqual(
            read['inventory_level_gid'], 'gid://shopify/InventoryLevel/1',
        )


@tagged('post_install', '-at_install')
class TestInventoryPreC2RecoverySeam(TransactionCase):
    """Genuine PostgreSQL independent-connection proof (mirrors core's
    own `TestMutationConcurrency` pattern) that the inherited pre-C2
    recovery seam -- never a domain-side commit inside
    `prepare_preconditions` itself -- durably applies this domain's
    blocked disposition only after core's own rollback/reset (PR #182
    comment 5028910116 item 3). A plain `TransactionCase`'s own
    uncommitted transaction is never visible to a separate `db_connect`
    connection, so this fixture is created and committed through its own
    independent connection, exactly like core's own
    `TestMutationConcurrency._durable_fixture`.
    """

    def _durable_fixture(self):
        domain = 'inventory-precc2-%s.myshopify.com' % uuid.uuid4().hex
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Inventory pre-C2 recovery seam',
                'shop_domain': domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            token = uuid.uuid4().hex
            job = env['shopify.connector.job'].sudo().create({
                'store_id': store.id,
                'job_source': 'scheduled_sync',
                'job_type': 'inventory_set_quantities',
                'state': 'running',
                'current_attempt_token': token,
                'owner_worker_ref': 'inventory-precc2:1',
                'running_since': fields.Datetime.now(),
                'started_at': fields.Datetime.now(),
                'payload_hash': uuid.uuid4().hex,
                'expected_connection_generation': store.connection_generation,
            })
            ids = store.id, job.id, token
            cr.commit()
        self.addCleanup(self._cleanup_fixture, store.id, job.id)
        return ids

    def _cleanup_fixture(self, store_id, job_id):
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job_log WHERE job_id = %s',
                (job_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_mutation_attempt '
                'WHERE job_id = %s',
                (job_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE id = %s', (job_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()

    def test_pre_c2_fail_closed_recovery_seam_applies_domain_disposition(self):
        _store_id, job_id, token = self._durable_fixture()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                job_id, token,
                InventoryPreC2FailClosedError(
                    'inventory_location_missing',
                    'inventory_location_missing',
                    'Fresh pre-C2 read found no Shopify inventory level.',
                ),
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(job.state, 'blocked_manual_review')
            self.assertEqual(job.error_class, 'inventory_location_missing')
            self.assertEqual(
                job.manual_review_subreason, 'inventory_location_missing',
            )
            self.assertFalse(job.current_attempt_token)
            self.assertEqual(
                env['shopify.connector.mutation.attempt'].search_count([
                    ('job_id', '=', job_id),
                ]),
                0,
            )

    def test_pre_c2_recovery_delegates_unrelated_exceptions_to_super(self):
        """A non-domain exception (e.g. a genuine pre-C2 transport
        failure) must still receive core's own generic bounded-retry
        recovery, never this domain's blocked disposition."""
        _store_id, job_id, token = self._durable_fixture()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                job_id, token, RuntimeError('synthetic pre-C2 failure'),
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(job.state, 'retry_waiting')

    # ------------------------------------------------------------------
    # Activation-superseded recovery (PR #182 comment 5029906989 item 3)
    # -- also genuinely commits (LL-005), so it needs the same
    # independent-connection proof as the fail-closed seam above.
    # ------------------------------------------------------------------

    def _durable_activation_fixture(self):
        domain = 'inventory-activate-superseded-%s.myshopify.com' % (
            uuid.uuid4().hex,
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Inventory activation-superseded recovery seam',
                'shop_domain': domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            warehouse = env['stock.warehouse'].search(
                [('company_id', '=', env.company.id)], limit=1,
            )
            location = env['stock.location'].create({
                'name': 'Activation superseded location',
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
            })
            mapping = env['shopify.connector.location.mapping'].sudo().create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Location/%s' % uuid.uuid4().hex[:8],
                'odoo_location_id': location.id,
                'match_key': 'manual',
            })
            template = env['product.template'].create({
                'name': 'Activation superseded product',
            })
            template_binding = env[
                'shopify.connector.product.template.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Product/%s' % uuid.uuid4().hex[:8],
                'product_template_id': template.id,
            })
            variant_binding = env[
                'shopify.connector.product.variant.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid':
                    'gid://shopify/ProductVariant/%s' % uuid.uuid4().hex[:8],
                'product_variant_id': template.product_variant_id.id,
                'product_template_binding_id': template_binding.id,
            })
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].sudo().create({
                'store_id': store.id,
                'product_variant_binding_id': variant_binding.id,
                'location_mapping_id': mapping.id,
                'shopify_inventory_item_gid':
                    'gid://shopify/InventoryItem/%s' % uuid.uuid4().hex[:8],
                'first_push_state': 'confirmed',
            })
            token = uuid.uuid4().hex
            job = env['shopify.connector.job'].sudo().create({
                'store_id': store.id,
                'job_source': 'scheduled_sync',
                'job_type': 'inventory_activate',
                'state': 'running',
                'current_attempt_token': token,
                'owner_worker_ref': 'inventory-activate-superseded:1',
                'running_since': fields.Datetime.now(),
                'started_at': fields.Datetime.now(),
                'payload_hash': uuid.uuid4().hex,
                'res_model': 'shopify.connector.inventory.level.binding',
                'res_id': binding.id,
                'expected_connection_generation': store.connection_generation,
            })
            ids = store.id, binding.id, job.id, token
            cr.commit()
        self.addCleanup(self._cleanup_activation_fixture, *ids)
        return ids

    def _cleanup_activation_fixture(self, store_id, binding_id, job_id, _token):
        with db_connect(self.env.cr.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job_log WHERE job_id IN '
                '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_mutation_attempt WHERE '
                'job_id IN (SELECT id FROM shopify_connector_job WHERE '
                'store_id = %s)',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_inventory_level_binding '
                'WHERE id = %s', (binding_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_product_variant_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_product_template_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_location_mapping WHERE '
                'store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()

    def test_activation_superseded_recovery_skips_and_hands_off(self):
        """A valid InventoryLevel already existing when
        `inventory_activate` reaches its own pre-C2 read must skip this
        job (never send an activation mutation) and durably hand off to
        exactly one fresh `inventory_push_sync`, entirely inside the
        seam's own committed recovery transaction (LL-005)."""
        from odoo.addons.shopify_connector_inventory.models.\
            shopify_connector_inventory_service import (
                InventoryActivationSupersededError,
            )
        _store_id, binding_id, job_id, token = self._durable_activation_fixture()
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                job_id, token,
                InventoryActivationSupersededError(
                    'gid://shopify/InventoryLevel/already-present',
                ),
            )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            self.assertEqual(job.state, 'skipped')
            self.assertFalse(
                env['shopify.connector.mutation.attempt'].search_count([
                    ('job_id', '=', job_id),
                ])
            )
            successors = env['shopify.connector.job'].search([
                ('job_type', '=', 'inventory_push_sync'),
                ('res_id', '=', binding_id),
            ])
            self.assertEqual(len(successors), 1)
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(binding_id)
            self.assertEqual(
                binding.shopify_gid,
                'gid://shopify/InventoryLevel/already-present',
            )
