import uuid

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


class TestFulfillmentInboundClassification(TransactionCase):
    """Origin classification (Modes §3) + observation routing (Modes §5).

    The own-GID ledger is authoritative: a Fulfillment GID that matches an
    existing fulfillment.binding is ('connector', True). An unrelated GID with an
    unresolved outbound create attempt on the order is ('external_unknown', False)
    -- unknown-pending, never confirmed external. An unrelated GID with no pending
    attempt is ('external_merchant', True). Observation records evidence: a
    connector-origin fulfillment is marked applied (never re-validated); a Mode 1
    external one opens a review case (no Odoo stock change).
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
        cls.sale_line = cls.env['sale.order.line'].create({
            'order_id': cls.sale.id, 'product_id': cls.product.id,
            'product_uom_qty': 2.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/111',
        })
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

    # ------------------------------------------------------------------
    # Fixture builders
    # ------------------------------------------------------------------

    def _fulfillment_binding(self, fulfillment_gid):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': fulfillment_gid,
            'picking_id': self.picking.id,
            'order_binding_id': self.order_binding.id,
            'status': 'active',
        })

    def _running_create_job(self):
        """A running fulfillment_create mutation job on the order's picking."""
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': 'fulfillment_picking_validation',
            'job_type': 'fulfillment_create',
            'state': 'queued',
            'res_model': 'stock.picking',
            'res_id': self.picking.id,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/1',
            'payload_hash': uuid.uuid4().hex,
        })
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        return job, token

    def _pending_attempt(self, job, token):
        """A post-C2 durable attempt intent left pending (effective disposition
        'unresolved') via the C2 side-cursor sentinel idiom."""
        return self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'fulfillment_create',
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {},
            'preconditions_snapshot': {'order_gid': self.order_binding.shopify_gid},
            'business_intent_fingerprint': 'bif',
            'exact_request_fingerprint': 'erf',
            'shopify_idempotency_key': '',
        })

    @staticmethod
    def _node(fulfillment_gid, status='SUCCESS', tracking=None):
        return {
            'id': fulfillment_gid,
            'status': status,
            'displayStatus': 'FULFILLED',
            'trackingInfo': tracking if tracking is not None else [],
        }

    # ------------------------------------------------------------------
    # _classify_origin: own-GID ledger authoritative
    # ------------------------------------------------------------------

    def test_connector_gid_from_own_ledger(self):
        fgid = 'gid://shopify/Fulfillment/CONN1'
        self._fulfillment_binding(fgid)
        origin_class, confirmed = self.Service._classify_origin(
            self.store, self.order_binding, fgid,
        )
        self.assertEqual(origin_class, 'connector')
        self.assertTrue(confirmed)

    def test_unknown_pending_with_unresolved_create_attempt(self):
        job, token = self._running_create_job()
        attempt = self._pending_attempt(job, token)
        # A pending attempt is an unresolved outbound op that might still be ours.
        self.assertEqual(attempt.effective_disposition(), 'unresolved')
        origin_class, confirmed = self.Service._classify_origin(
            self.store, self.order_binding, 'gid://shopify/Fulfillment/UNK1',
        )
        self.assertEqual(origin_class, 'external_unknown')
        self.assertFalse(confirmed)

    def test_external_merchant_when_no_pending_attempt(self):
        # No pending fulfillment_create attempt exists for the order's pickings.
        origin_class, confirmed = self.Service._classify_origin(
            self.store, self.order_binding, 'gid://shopify/Fulfillment/EXT1',
        )
        self.assertEqual(origin_class, 'external_merchant')
        self.assertTrue(confirmed)

    # ------------------------------------------------------------------
    # _observe_fulfillment: evidence + routing
    # ------------------------------------------------------------------

    def test_observe_connector_marks_applied_never_revalidated(self):
        fgid = 'gid://shopify/Fulfillment/CONN2'
        self._fulfillment_binding(fgid)
        node = self._node(fgid, tracking=[{'number': 'TN1', 'url': '', 'company': 'UPS'}])
        evidence = self.Service._observe_fulfillment(
            self.store, self.order_binding, node, 'mode1',
        )
        self.assertEqual(evidence.origin_class, 'connector')
        self.assertTrue(evidence.origin_confirmed)
        # Connector-origin confirms our own outbound op -> applied, not review.
        self.assertEqual(evidence.reconciled_state, 'applied')

    def test_observe_external_mode1_opens_review_case(self):
        fgid = 'gid://shopify/Fulfillment/EXT2'
        node = self._node(fgid)
        evidence = self.Service._observe_fulfillment(
            self.store, self.order_binding, node, 'mode1',
        )
        self.assertEqual(evidence.origin_class, 'external_merchant')
        # Mode 1 external -> a review case, zero automatic Odoo stock change.
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'remote_state_changed')

    def test_observe_external_unknown_mode1_review_origin_unconfirmed(self):
        job, token = self._running_create_job()
        self._pending_attempt(job, token)
        fgid = 'gid://shopify/Fulfillment/UNK2'
        node = self._node(fgid)
        evidence = self.Service._observe_fulfillment(
            self.store, self.order_binding, node, 'mode1',
        )
        self.assertEqual(evidence.origin_class, 'external_unknown')
        self.assertFalse(evidence.origin_confirmed)
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'origin_unconfirmed')
