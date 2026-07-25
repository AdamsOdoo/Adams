import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
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
class TestFulfillmentPickingAdmission(TransactionCase):
    """`_handle_fulfillment_picking_admission` decomposes a validated outbound
    picking into exactly one `fulfillment_create` child (a picking is one
    physical shipment -> one Shopify fulfillment). It fails closed on a blocking
    FulfillmentOrder status (`ambiguous_match`) and on an unmatched shipped line
    (`mapping_missing`), and is idempotent once a fulfillment binding exists.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Service = cls.env['shopify.connector.fulfillment.service']
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
        # The core location cache row the create-eligibility path resolves to.
        cls.env['shopify.connector.location'].sudo().create({
            'store_id': cls.store.id,
            'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'L', 'shopify_location_active': True,
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _picking(self, line_specs):
        """Build an outbound picking with one shipped move line per spec.

        `line_specs` is a list of (shopify_line_item_gid, quantity).
        """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            ).id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        for gid, qty in line_specs:
            sale_line = self.env['sale.order.line'].create({
                'order_id': self.sale.id, 'product_id': self.product.id,
                'product_uom_qty': qty, 'shopify_line_item_gid': gid,
            })
            move = self.env['stock.move'].create({
                # Odoo 19 removed stock.move.name (computed `reference` instead).
                'product_id': self.product.id,
                'product_uom_qty': qty, 'product_uom': self.product.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
                'sale_line_id': sale_line.id,
            })
            self.env['stock.move.line'].create({
                'move_id': move.id, 'product_id': self.product.id,
                'quantity': qty, 'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
            })
        return picking

    def _fo(self, fo_id, line_specs, status='OPEN',
            location='gid://shopify/Location/1',
            actions=('CREATE_FULFILLMENT',)):
        """A FulfillmentOrder node as `_read_fulfillment_orders` returns it
        (line items already attached under 'line_items').

        `line_specs` is a list of (fo_line_id, remaining_quantity,
        order_line_item_gid).
        """
        return {
            'id': fo_id,
            'status': status,
            'requestStatus': 'SUBMITTED',
            'assignedLocation': {'location': {'id': location, 'name': 'L'}},
            'supportedActions': [{'action': a} for a in actions],
            'line_items': [
                {'id': fid, 'remainingQuantity': rem, 'lineItem': {'id': li}}
                for (fid, rem, li) in line_specs
            ],
        }

    def _admission_job(self, picking):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'odoo_event',
            'trigger_origin': 'fulfillment_picking_validation',
            'job_type': 'fulfillment_picking_admission',
            'state': 'queued',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'payload_hash': uuid.uuid4().hex,
        })

    def _create_jobs(self, picking):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'fulfillment_create'),
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', picking.id),
        ])

    # ------------------------------------------------------------------
    # Happy path: exactly one fulfillment_create per picking
    # ------------------------------------------------------------------

    def test_one_create_job_per_picking(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        job = self._admission_job(picking)
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 2,
              'gid://shopify/LineItem/111')],
        )]
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=fos,
        ):
            self.Service._handle_fulfillment_picking_admission(job)
        created = self._create_jobs(picking)
        self.assertEqual(len(created), 1)
        self.assertEqual(created.res_model, 'stock.picking')
        self.assertEqual(created.res_id, picking.id)
        self.assertEqual(
            created.shopify_target_gid, 'gid://shopify/FulfillmentOrder/1',
        )
        # job_source is inherited from the admission job; trigger_origin too.
        self.assertEqual(created.job_source, 'odoo_event')
        self.assertEqual(
            created.trigger_origin, 'fulfillment_picking_validation',
        )

    def test_two_fos_one_location_yield_single_create_with_min_gid(self):
        # Two FOs at one location, each shipping one line on this picking:
        # still ONE create job spanning them, with the representative
        # (minimum) FulfillmentOrder GID as the target.
        picking = self._picking([
            ('gid://shopify/LineItem/111', 2.0),
            ('gid://shopify/LineItem/222', 2.0),
        ])
        job = self._admission_job(picking)
        fos = [
            self._fo(
                'gid://shopify/FulfillmentOrder/2',
                [('gid://shopify/FulfillmentOrderLineItem/2', 2,
                  'gid://shopify/LineItem/222')],
            ),
            self._fo(
                'gid://shopify/FulfillmentOrder/1',
                [('gid://shopify/FulfillmentOrderLineItem/1', 2,
                  'gid://shopify/LineItem/111')],
            ),
        ]
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=fos,
        ):
            self.Service._handle_fulfillment_picking_admission(job)
        created = self._create_jobs(picking)
        self.assertEqual(len(created), 1)
        self.assertEqual(
            created.shopify_target_gid, 'gid://shopify/FulfillmentOrder/1',
        )

    # ------------------------------------------------------------------
    # Fail-closed routing
    # ------------------------------------------------------------------

    def test_unmatched_shipped_line_routes_mapping_missing(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        job = self._admission_job(picking)
        # The FO is eligible but its line matches a different order line item.
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 2,
              'gid://shopify/LineItem/999')],
        )]
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=fos,
        ):
            with self.assertRaises(JobHandlerError) as cm:
                self.Service._handle_fulfillment_picking_admission(job)
        self.assertEqual(cm.exception.error_class, 'mapping_missing')
        self.assertFalse(self._create_jobs(picking))

    def test_blocking_fo_status_routes_ambiguous_match(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        job = self._admission_job(picking)
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 2,
              'gid://shopify/LineItem/111')],
            status='ON_HOLD',
        )]
        with patch.object(
            type(self.Service), '_read_fulfillment_orders', return_value=fos,
        ):
            with self.assertRaises(JobHandlerError) as cm:
                self.Service._handle_fulfillment_picking_admission(job)
        self.assertEqual(cm.exception.error_class, 'ambiguous_match')
        self.assertFalse(self._create_jobs(picking))

    # ------------------------------------------------------------------
    # Idempotency: one picking is one fulfillment event
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Theme A — centralized `_enqueue_once` collision recovery
    # ------------------------------------------------------------------

    def test_duplicate_admission_enqueue_collision_returns_existing_job(self):
        # Two _enqueue_once calls for the SAME picking under the SAME
        # job_type but with different payload_hash: the fast idempotency-key
        # search misses (different hash), so the DB-level operation-scope-
        # key collision genuinely fires -- the loser must recover by
        # returning the winner's existing job, with the caller's cursor
        # remaining fully usable afterward (never a poisoned transaction).
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        first = self.Service._enqueue_once(
            self.store, 'odoo_event', 'fulfillment_picking_admission',
            'admission:%d:first' % picking.id, 'stock.picking', picking.id,
            trigger_origin='fulfillment_picking_validation',
        )
        self.assertTrue(first)
        second = self.Service._enqueue_once(
            self.store, 'odoo_event', 'fulfillment_picking_admission',
            'admission:%d:second' % picking.id, 'stock.picking', picking.id,
            trigger_origin='fulfillment_picking_validation',
        )
        self.assertEqual(second, first)
        # The caller's cursor remains usable after the internally-recovered
        # collision -- a subsequent, unrelated ORM call succeeds normally.
        self.assertTrue(self.env['shopify.connector.store'].search(
            [('id', '=', self.store.id)],
        ))

    def test_unexpected_enqueue_exception_propagates(self):
        # An exception outside the caught (ValidationError, IntegrityError)
        # tuple must propagate unchanged, never silently absorbed as if it
        # were the benign collision.
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        with patch.object(
            type(self.env['shopify.connector.job.enqueue']), 'enqueue',
            side_effect=ValueError('genuinely unrelated failure'),
        ):
            with self.assertRaises(ValueError):
                self.Service._enqueue_once(
                    self.store, 'odoo_event', 'fulfillment_picking_admission',
                    'admission:%d:unexpected' % picking.id,
                    'stock.picking', picking.id,
                    trigger_origin='fulfillment_picking_validation',
                )

    def test_validation_error_with_unrelated_message_propagates(self):
        # A genuine ValidationError whose message does NOT match the exact
        # operation-scope-collision message/constraint name must also
        # propagate unchanged -- the match is on the specific constraint,
        # never any ValidationError.
        from odoo.exceptions import ValidationError
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        with patch.object(
            type(self.env['shopify.connector.job.enqueue']), 'enqueue',
            side_effect=ValidationError('An unrelated validation failure.'),
        ):
            with self.assertRaises(ValidationError):
                self.Service._enqueue_once(
                    self.store, 'odoo_event', 'fulfillment_picking_admission',
                    'admission:%d:unrelated-validation' % picking.id,
                    'stock.picking', picking.id,
                    trigger_origin='fulfillment_picking_validation',
                )

    # ------------------------------------------------------------------
    # Correction P0-2 — anti-redundant-admission
    # ------------------------------------------------------------------

    def test_enqueue_picking_admission_skips_when_binding_already_exists(self):
        # When the picking already carries a fulfillment binding (the
        # inbound Mode-2 apply creates one inside its own atomic savepoint
        # immediately before calling _action_done()), the outbound picking-
        # admission enqueue seam must be a pure no-op -- no redundant
        # fulfillment_create is ever queued for a fulfillment the connector
        # already knows this picking IS.
        picking = self._picking([('gid://shopify/LineItem/REDUNDANT', 2.0)])
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/REDUNDANT',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        before = self.Job.search_count([
            ('job_type', '=', 'fulfillment_picking_admission'),
        ])
        with patch.object(
            type(self.Service), '_enqueue_once',
            side_effect=AssertionError(
                'must not enqueue when a binding already exists'),
        ):
            result = self.Service._enqueue_picking_admission(picking)
        after = self.Job.search_count([
            ('job_type', '=', 'fulfillment_picking_admission'),
        ])
        self.assertFalse(result)
        self.assertEqual(after, before)

    def test_existing_binding_short_circuits_before_read(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/1',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        job = self._admission_job(picking)
        # The reader must never be consulted once the picking is already bound.
        with patch.object(
            type(self.Service), '_read_fulfillment_orders',
            side_effect=AssertionError('must not read after binding exists'),
        ):
            result = self.Service._handle_fulfillment_picking_admission(job)
        self.assertIsNone(result)
        self.assertFalse(self._create_jobs(picking))
