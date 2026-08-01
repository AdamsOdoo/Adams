# Part of the Shopify Connector (Store 360 slice 1).
#
# The eleven protected sale-order projection columns: sanctioned writers,
# fail-closed refusal of every unsanctioned write (ordinary, RPC-shaped and
# elevated), company consistency, quarantine propagation, replay
# convergence, copy() hygiene, and the idempotent backfill migration.
#
# COUNTERFACTUAL PROPERTY: none of these fields exist at a1c5931 (there is
# no `sale.order` extension anywhere in the connector at that head), so
# this file fails to even reference them there.

import importlib.util
import os

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.shopify_connector_sale.models.shopify_connector_sale_order_projection import (
    PROJECTION_SANCTION_KEY,
    SALE_ORDER_PROJECTION_FIELDS,
)

from .test_order_import_mapping import OrderImportCase


@tagged('post_install', '-at_install')
class TestSaleOrderProjection(OrderImportCase):

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------
    def _order(self):
        return self.env['sale.order'].sudo().create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
        })

    def _bind(self, order, suffix, **extra):
        vals = {
            'store_id': self.store.id,
            'sale_order_id': order.id,
            'shopify_gid': 'gid://shopify/Order/%s' % suffix,
            'shopify_order_name': '#%s' % suffix,
        }
        vals.update(extra)
        return self.Binding.sudo().create(vals)

    # ------------------------------------------------------------------
    # the schema itself
    # ------------------------------------------------------------------
    def test_the_projection_is_exactly_eleven_stored_fields(self):
        Order = self.env['sale.order']
        self.assertEqual(len(SALE_ORDER_PROJECTION_FIELDS), 11)
        for name in SALE_ORDER_PROJECTION_FIELDS:
            field = Order._fields.get(name)
            self.assertIsNotNone(field, 'missing projection field %s' % name)
            self.assertTrue(field.store, '%s must be stored' % name)
            self.assertFalse(field.copy, '%s must not survive copy()' % name)

    # ------------------------------------------------------------------
    # sanctioned writers: the binding choke point
    # ------------------------------------------------------------------
    def test_binding_create_projects_onto_the_order(self):
        order = self._order()
        self._bind(
            order, 'Proj1',
            shopify_financial_status_snapshot='PAID',
            shopify_fulfillment_status_snapshot='UNFULFILLED',
            is_cod=False,
            shopify_last_evidence_refresh_at=fields.Datetime.now(),
        )
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_store_id, self.store)
        self.assertEqual(order.shopify_connector_financial_status, 'PAID')
        self.assertEqual(
            order.shopify_connector_fulfillment_status, 'UNFULFILLED')
        self.assertFalse(order.shopify_connector_is_cod)
        self.assertFalse(order.shopify_connector_review)
        self.assertFalse(order.shopify_connector_quarantined)

    def test_binding_lifecycle_writes_mirror_in_the_same_transaction(self):
        order = self._order()
        binding = self._bind(order, 'Proj2', is_cod=True,
                             manual_gateway_approval_state='pending',
                             cod_commercial_state='quotation')
        order.invalidate_recordset()
        self.assertTrue(order.shopify_connector_is_cod)
        self.assertEqual(order.shopify_connector_approval_state, 'pending')
        self.assertEqual(
            order.shopify_connector_cod_commercial_state, 'quotation')
        binding.sudo().write({
            'status': 'review',
            'manual_gateway_approval_state': 'superseded',
            'shopify_cancelled_at': fields.Datetime.now(),
        })
        order.invalidate_recordset()
        self.assertTrue(order.shopify_connector_review)
        self.assertEqual(
            order.shopify_connector_approval_state, 'superseded')
        self.assertTrue(order.shopify_connector_cancelled_at)

    def test_the_real_importer_route_projects(self):
        """The full production import path (payload → order + binding)
        leaves a correctly projected order."""
        binding = self.Importer._apply_import(
            self.store, self._payload('gid://shopify/Order/ProjImp'),
        )
        order = binding.sale_order_id
        self.assertEqual(order.shopify_connector_store_id, self.store)
        self.assertEqual(
            order.shopify_connector_financial_status,
            binding.shopify_financial_status_snapshot,
        )
        self.assertEqual(
            order.shopify_connector_evidence_refreshed_at,
            binding.shopify_last_evidence_refresh_at,
        )

    def test_replayed_write_converges_without_drift(self):
        order = self._order()
        binding = self._bind(order, 'Proj3',
                             shopify_financial_status_snapshot='PENDING')
        binding.sudo().write(
            {'shopify_financial_status_snapshot': 'PENDING'})
        binding.sudo().write(
            {'shopify_financial_status_snapshot': 'PENDING'})
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_financial_status, 'PENDING')

    # ------------------------------------------------------------------
    # fail-closed write surface
    # ------------------------------------------------------------------
    def test_every_role_is_refused_a_direct_projection_write(self):
        order = self._order()
        self._bind(order, 'Proj4')
        for role, user in self.roles.items():
            with self.subTest(role=role):
                with self.assertRaises(AccessError):
                    order.with_user(user).write(
                        {'shopify_connector_is_cod': True})

    def test_elevated_but_unsanctioned_write_is_refused(self):
        order = self._order()
        self._bind(order, 'Proj5')
        with self.assertRaises(AccessError):
            order.sudo().write({'shopify_connector_review': True})
        with self.assertRaises(AccessError):
            self.env['sale.order'].sudo().create({
                'partner_id': self.fallback_partner.id,
                'shopify_connector_store_id': self.store.id,
            })

    def test_unsanctioned_write_leaves_no_side_effect(self):
        order = self._order()
        self._bind(order, 'Proj6',
                   shopify_financial_status_snapshot='PAID')
        order.invalidate_recordset()
        before = order.shopify_connector_financial_status
        with self.assertRaises(AccessError):
            order.sudo().write(
                {'shopify_connector_financial_status': 'VOIDED'})
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_financial_status, before)

    # ------------------------------------------------------------------
    # company consistency
    # ------------------------------------------------------------------
    def test_cross_company_projection_is_refused(self):
        other_company = self.env['res.company'].sudo().create(
            {'name': 'Projection Other Co'})
        other_order = self.env['sale.order'].sudo().create({
            'partner_id': self.fallback_partner.id,
            'company_id': other_company.id,
        })
        # sale.order._check_company_auto is True at the pin
        # (sale/models/sale_order.py:39), so check_company refuses the
        # cross-company store even through the sanctioned path. (Odoo's
        # assertRaises helper takes a single class; UserError is the
        # documented check_company refusal and ValidationError subclasses
        # nothing that would slip past it here.)
        with self.assertRaises(UserError):
            other_order.sudo().with_context(
                **{PROJECTION_SANCTION_KEY: True}
            ).write({'shopify_connector_store_id': self.store.id})

    def test_projection_store_must_agree_with_the_binding_store(self):
        order = self._order()
        self._bind(order, 'Proj7')
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_store_id, self.store)

    # ------------------------------------------------------------------
    # quarantine propagation (both the ORM path and the SQL sweep hook)
    # ------------------------------------------------------------------
    def test_quarantine_orm_write_propagates(self):
        order = self._order()
        binding = self._bind(order, 'Proj8')
        binding.sudo().write({'sec3_scope_quarantined': True})
        order.invalidate_recordset()
        self.assertTrue(order.shopify_connector_quarantined)
        binding.sudo().write({'sec3_scope_quarantined': False})
        order.invalidate_recordset()
        self.assertFalse(order.shopify_connector_quarantined)

    def test_quarantine_sql_hook_propagates_in_the_same_transaction(self):
        order = self._order()
        binding = self._bind(order, 'Proj9')
        # The SEC-3 sweep/release write the flag in SQL and then invoke the
        # hook; drive exactly that shape.
        self.env.cr.execute(
            'UPDATE shopify_connector_order_binding '
            'SET sec3_scope_quarantined = TRUE WHERE id = %s',
            (binding.id,),
        )
        self.Binding.invalidate_model(['sec3_scope_quarantined'])
        self.Binding._sec3_after_quarantine_flag_update([binding.id], True)
        order.invalidate_recordset()
        self.assertTrue(order.shopify_connector_quarantined)
        self.env.cr.execute(
            'UPDATE shopify_connector_order_binding '
            'SET sec3_scope_quarantined = FALSE WHERE id = %s',
            (binding.id,),
        )
        self.Binding.invalidate_model(['sec3_scope_quarantined'])
        self.Binding._sec3_after_quarantine_flag_update([binding.id], False)
        order.invalidate_recordset()
        self.assertFalse(order.shopify_connector_quarantined)

    # ------------------------------------------------------------------
    # copy() hygiene
    # ------------------------------------------------------------------
    def test_duplicating_an_order_does_not_duplicate_the_projection(self):
        order = self._order()
        self._bind(order, 'Proj10',
                   shopify_financial_status_snapshot='PAID')
        order.invalidate_recordset()
        duplicate = order.sudo().copy()
        self.assertFalse(duplicate.shopify_connector_store_id)
        self.assertFalse(duplicate.shopify_connector_financial_status)

    # ------------------------------------------------------------------
    # backfill migration: populates and is idempotent
    # ------------------------------------------------------------------
    def _run_backfill(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'migrations', '19.0.2.9.0', 'post-migrate.py',
        )
        spec = importlib.util.spec_from_file_location('sc_backfill', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '19.0.2.8.0')

    def test_backfill_repopulates_and_reruns_to_zero(self):
        order = self._order()
        self._bind(order, 'Proj11',
                   shopify_financial_status_snapshot='PAID', is_cod=True)
        self.env.flush_all()
        # Blank the projection at the SQL level (simulating a pre-upgrade
        # database whose columns exist but were never populated).
        self.env.cr.execute(
            'UPDATE sale_order SET shopify_connector_store_id = NULL, '
            'shopify_connector_financial_status = NULL, '
            'shopify_connector_is_cod = FALSE WHERE id = %s',
            (order.id,),
        )
        self._run_backfill()
        first_pass = self.env.cr.rowcount
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_store_id, self.store)
        self.assertEqual(order.shopify_connector_financial_status, 'PAID')
        self.assertTrue(order.shopify_connector_is_cod)
        # Second run converges to zero touched rows: idempotent.
        self._run_backfill()
        self.assertEqual(self.env.cr.rowcount, 0)
        self.assertGreaterEqual(first_pass, 1)
