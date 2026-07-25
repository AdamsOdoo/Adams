import uuid
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    INCONCLUSIVE_RECONCILIATION_CAP,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (
    FulfillmentReadError,
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
class TestFulfillmentIdempotency(TransactionCase):
    """The P0 mutation-safety contract: reconcile-only after C2, no resend from
    read absence, post-C2 has only APPLIED / INCONCLUSIVE, the shared reconcile
    cannot enqueue a mutation, and no-tracking / possible-notification
    uncertainty fails closed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })

    def _mutation_job(self, domain='fulfillment_create'):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': 'fulfillment_picking_validation',
            'job_type': domain,
            'state': 'queued',
            'res_model': 'stock.picking',
            'res_id': 1,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/1',
            'payload_hash': uuid.uuid4().hex,
        })
        job.sudo().write({
            'state': 'running', 'current_attempt_token': token,
        })
        return job, token

    def _uncertain_attempt(self, job, token, domain='fulfillment_create', snapshot=None):
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': domain,
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {},
            'preconditions_snapshot': snapshot or {'order_gid': 'gid://shopify/Order/1'},
            'business_intent_fingerprint': 'bif',
            'exact_request_fingerprint': 'erf',
            'shopify_idempotency_key': '',
        })
        attempt._record_direct_outcome('uncertain', evidence={})
        return attempt

    def _reconcile_job(self, attempt):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'fulfillment_mutation_reconcile',
            'state': 'running',
            'mutation_attempt_id': attempt.id,
            'payload_hash': 'reconcile:%s' % attempt.attempt_token,
            'expected_connection_generation': attempt.expected_connection_generation,
        })

    def _stub_reconcile(self, verdict):
        strat = dict(self.Dispatch._get_reconciliation_strategies()['fulfillment_create'])
        strat['transport'] = Mock(side_effect=AssertionError('transport must never replay'))
        result = {
            'verdict': verdict,
            'observed_store_identity': self.store.shop_domain,
            'action': 'succeed' if verdict == 'applied' else None,
            'error_class': None, 'manual_review_subreason': None,
            'message': 'stub', 'evidence': {},
        }
        if verdict == 'applied':
            result['domain_payload'] = {'adopted_fulfillment_gid': 'gid://shopify/Fulfillment/1'}
        strat['reconcile'] = lambda attempt: result
        return strat

    # ------------------------------------------------------------------

    def test_transport_attempted_true_after_c2(self):
        job, token = self._mutation_job()
        attempt = self._uncertain_attempt(job, token)
        self.assertTrue(attempt.transport_attempted)

    def test_cap_constant_is_three(self):
        self.assertEqual(INCONCLUSIVE_RECONCILIATION_CAP, 3)

    def test_inconclusive_retries_then_caps_to_duplicate_risk(self):
        job, token = self._mutation_job()
        attempt = self._uncertain_attempt(job, token)
        strat = self._stub_reconcile('inconclusive')
        before = self.Job.search_count([
            ('job_type', 'in', ('fulfillment_create', 'fulfillment_tracking_update')),
        ])
        recon = self._reconcile_job(attempt)
        with patch.object(type(self.Dispatch), '_get_reconciliation_strategies',
                          return_value={'fulfillment_create': strat}):
            for i in range(INCONCLUSIVE_RECONCILIATION_CAP):
                if i:
                    recon.sudo().write({'state': 'running'})
                self.Dispatch._handle_fulfillment_mutation_reconcile(recon)
                attempt.invalidate_recordset()
                recon.invalidate_recordset()
        job.invalidate_recordset()
        # After the cap, the ORIGINAL mutation job is blocked as duplicate_risk.
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')
        self.assertEqual(job.error_class, 'duplicate_risk')
        # No second mutation job was ever enqueued from the read result.
        after = self.Job.search_count([
            ('job_type', 'in', ('fulfillment_create', 'fulfillment_tracking_update')),
        ])
        self.assertEqual(after, before)
        # The transport callback was never called from reconciliation.
        strat['transport'].assert_not_called()

    def test_read_absence_is_inconclusive_never_not_applied(self):
        job, token = self._mutation_job()
        snapshot = {'order_gid': 'gid://shopify/Order/1', 'sent_tracking_numbers': ['TN1']}
        attempt = self._uncertain_attempt(job, token, snapshot=snapshot)
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          return_value=[]):
            result = self.Service._reconcile_fulfillment_create(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertNotEqual(result['verdict'], 'not_applied')

    def test_no_tracking_uncertainty_fails_closed(self):
        # SRR-10: a no-tracking fulfillment whose FO remaining did not decrease
        # by exactly the sent quantities under concurrent activity -> inconclusive.
        job, token = self._mutation_job()
        snapshot = {
            'order_gid': 'gid://shopify/Order/1',
            'sent_tracking_numbers': [],
            'line_items_by_fo': [{'fulfillmentOrderId': 'gid://shopify/FulfillmentOrder/1',
                                  'fulfillmentOrderLineItems': [
                                      {'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 2}]}],
            'fo_remaining_snapshot': {'gid://shopify/FulfillmentOrderLineItem/1': 2},
        }
        attempt = self._uncertain_attempt(job, token, snapshot=snapshot)
        fos = [{'id': 'gid://shopify/FulfillmentOrder/1', 'status': 'OPEN',
                'line_items': [{'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                                'remainingQuantity': 1}]}]  # decreased by 1, not 2
        with patch.object(type(self.Service), '_read_order_fulfillments', return_value=[]), \
             patch.object(type(self.Service), '_read_fulfillment_orders', return_value=fos):
            result = self.Service._reconcile_fulfillment_create(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_no_tracking_exact_decrease_is_applied(self):
        job, token = self._mutation_job()
        snapshot = {
            'order_gid': 'gid://shopify/Order/1',
            'sent_tracking_numbers': [],
            'line_items_by_fo': [{'fulfillmentOrderId': 'gid://shopify/FulfillmentOrder/1',
                                  'fulfillmentOrderLineItems': [
                                      {'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 2}]}],
            'fo_remaining_snapshot': {'gid://shopify/FulfillmentOrderLineItem/1': 2},
        }
        attempt = self._uncertain_attempt(job, token, snapshot=snapshot)
        fos = [{'id': 'gid://shopify/FulfillmentOrder/1', 'status': 'OPEN',
                'line_items': [{'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                                'remainingQuantity': 0}]}]  # decreased by exactly 2
        with patch.object(type(self.Service), '_read_order_fulfillments', return_value=[]), \
             patch.object(type(self.Service), '_read_fulfillment_orders', return_value=fos):
            result = self.Service._reconcile_fulfillment_create(attempt)
        self.assertEqual(result['verdict'], 'applied')

    def test_tracking_update_uncertainty_never_repeats_notification(self):
        job, token = self._mutation_job(domain='fulfillment_tracking_update')
        snapshot = {'fulfillment_gid': 'gid://shopify/Fulfillment/1',
                    'sent_tracking_numbers': ['TN1'], 'notify_customer': True}
        attempt = self._uncertain_attempt(job, token, domain='fulfillment_tracking_update',
                                          snapshot=snapshot)
        # Old/unchanged tracking observed -> inconclusive, never a resend.
        node = {'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
                'trackingInfo': [{'number': 'OLD'}]}
        with patch.object(type(self.Service), '_read_fulfillment', return_value=node):
            result = self.Service._reconcile_fulfillment_tracking_update(attempt)
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_shared_reconcile_never_produces_not_applied_verdict(self):
        # Even if a (hypothetical) callback returned not_applied, the shared
        # handler coerces it to inconclusive — post-C2 has only APPLIED /
        # INCONCLUSIVE.
        job, token = self._mutation_job()
        attempt = self._uncertain_attempt(job, token)
        strat = self._stub_reconcile('not_applied')
        recon = self._reconcile_job(attempt)
        with patch.object(type(self.Dispatch), '_get_reconciliation_strategies',
                          return_value={'fulfillment_create': strat}):
            self.Dispatch._handle_fulfillment_mutation_reconcile(recon)
        attempt.invalidate_recordset()
        # Recorded as an inconclusive reconciliation, not resolved not_applied.
        self.assertEqual(attempt.inconclusive_reconciliation_count, 1)
        self.assertFalse(attempt.resolution_disposition)

    # ------------------------------------------------------------------
    # P2 correction: Mode 2 condition 14's separately fresh read is a pure
    # local-evaluation read. It must never create mutation-attempt evidence
    # or authorize a resend -- that machinery belongs exclusively to the
    # C1/C2/NET/C3 mutation path exercised above, never to Mode 2's
    # read-only auto-application evaluator.
    # ------------------------------------------------------------------

    def _mode2_ctx(self, location_gid='gid://shopify/Location/1'):
        # Direct C14 context (Correction C): calling `_c14_remote_state` in
        # isolation bypasses Conditions 8/9, which normally establish
        # `mapped_odoo_location_id` and the selected `picking` in the real
        # 16-condition pipeline before Condition 14 ever runs. Supply that
        # same context explicitly: a real internal stock location, and a
        # picking test double whose `location_id` is that same location.
        stock_location = self.env.ref('stock.stock_location_stock')
        picking = Mock()
        picking.location_id = stock_location
        sale_line = Mock()
        sale_line.id = 1
        order_binding = Mock()
        order_binding.shopify_gid = 'gid://shopify/Order/1'
        evidence = Mock()
        evidence.shopify_fulfillment_gid = 'gid://shopify/Fulfillment/1'
        return {
            'store': self.store,
            'order_binding': order_binding,
            'evidence': evidence,
            'line_mapping': {
                'gid://shopify/LineItem/1': (sale_line, 2),
            },
            'location_gid': location_gid,
            'mapped_odoo_location_id': stock_location.id,
            'picking': picking,
            'plan': {},
        }

    def _mode2_second_read_fixture(self):
        node = {
            'id': 'gid://shopify/Fulfillment/1', 'status': 'SUCCESS',
            'fulfillmentLineItems': {'nodes': [{
                'id': 'gid://shopify/FulfillmentLineItem/1', 'quantity': 2,
                'lineItem': {'id': 'gid://shopify/LineItem/1'},
            }]},
        }
        fo = {
            'id': 'gid://shopify/FulfillmentOrder/1', 'status': 'OPEN',
            'assignedLocation': {
                'location': {'id': 'gid://shopify/Location/1'}},
        }
        self.env['shopify.connector.location'].sudo().create({
            'store_id': self.store.id,
            'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'L', 'shopify_location_active': True,
        })
        return node, fo

    def test_condition14_second_read_never_creates_mutation_attempt(self):
        ctx = self._mode2_ctx()
        node, fo = self._mode2_second_read_fixture()
        before = self.Attempt.search_count([])
        # Sanctioned seam (Correction C): the second FulfillmentOrder read
        # must re-confirm the SAME mapped Odoo location Conditions 8/9
        # already established in `ctx` (here: the picking's own
        # `location_id`), through `shopify.connector.location`'s own
        # extension point -- never a direct location-mapping read.
        LocationModel = type(self.env['shopify.connector.location'])
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          return_value=[node]), \
                patch.object(type(self.Service), '_read_fulfillment_orders',
                             return_value=[fo]), \
                patch.object(LocationModel, '_resolve_odoo_location',
                             return_value=ctx['picking'].location_id):
            ok, _detail = self.Service._c14_remote_state(ctx)
        self.assertTrue(ok)
        self.assertEqual(self.Attempt.search_count([]), before)

    def test_condition14_failed_second_read_does_not_authorize_resend(self):
        ctx = self._mode2_ctx()
        with patch.object(type(self.Service), '_read_order_fulfillments',
                          return_value=[]):
            ok, _detail = self.Service._c14_remote_state(ctx)
        self.assertFalse(ok)
        # No mutation-attempt evidence was created or made eligible for a
        # resend by this pure read-only local-evaluation condition.
        self.assertEqual(self.Attempt.search_count([]), 0)

    def test_condition14_unknown_read_outcome_remains_fail_closed(self):
        # An incomplete/malformed second read is an unknown outcome; it must
        # propagate (fail closed) rather than be silently treated as a pass.
        ctx = self._mode2_ctx()
        with patch.object(
            type(self.Service), '_read_order_fulfillments',
            side_effect=FulfillmentReadError(
                'data_shape_schema_mismatch', 'incomplete'),
        ):
            with self.assertRaises(FulfillmentReadError):
                self.Service._c14_remote_state(ctx)
        self.assertEqual(self.Attempt.search_count([]), 0)

    def test_preflight_blocks_redispatch_with_existing_attempt(self):
        job, token = self._mutation_job()
        self._uncertain_attempt(job, token)
        # A mutation job that already owns attempt evidence is blocked from
        # redispatch (duplicate_risk), never re-sent. Reach the re-queued state
        # via legal transitions (running -> failed_retryable -> queued): a
        # direct running -> queued write is correctly rejected by the core
        # transition guard.
        job.sudo().write({'state': 'failed_retryable'})
        job.sudo().write({'state': 'queued', 'current_attempt_token': False})
        blocked = self.Dispatch._preflight_existing_attempt_evidence(job)
        job.invalidate_recordset()
        self.assertTrue(blocked)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')
