# Part of the Shopify Connector (Store 360 slice 1).
#
# The eleven protected sale-order projection columns: the one non-forgeable
# private writer, fail-closed refusal of every unsanctioned write (ordinary,
# elevated, and — proven at the real request boundary — RPC with a forged
# context key or a private-method name), company + binding-store consistency,
# quarantine propagation, replay convergence, copy() hygiene, and the
# idempotent backfill migration.
#
# COUNTERFACTUAL PROPERTY: none of these fields exist at a1c5931 (there is
# no `sale.order` extension anywhere in the connector at that head), so
# this file fails to even reference them there.

import importlib.util
import os

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, JsonRpcException

from odoo.addons.shopify_connector_sale.models.shopify_connector_sale_order_projection import (
    SALE_ORDER_PROJECTION_FIELDS,
)

# The context key removed by the PR #204 P0-1 correction. The RPC regression
# below forges exactly this key to prove it no longer authorises anything.
_REMOVED_SANCTION_KEY = 'shopify_connector_projection_sanctioned_write'

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

    def test_no_context_key_authorises_a_projection_write(self):
        """The removed sanction key must not re-authorise anything, even
        supplied through `with_context` on a sudo recordset — the exact shape
        the P0-1 spoof used."""
        order = self._order()
        self._bind(order, 'Proj5b')
        with self.assertRaises(AccessError):
            order.sudo().with_context(
                **{_REMOVED_SANCTION_KEY: True}
            ).write({'shopify_connector_review': True})

    def test_private_writer_rejects_non_projection_fields(self):
        """The one sanctioned writer accepts only projection fields, so it can
        never be turned into a general back-door write."""
        order = self._order()
        self._bind(order, 'Proj5c')
        with self.assertRaises(ValueError):
            order.sudo()._shopify_connector_write_projection({'name': 'X'})
        with self.assertRaises(ValueError):
            order.sudo()._shopify_connector_write_projection({
                'shopify_connector_review': True,  # legitimate...
                'client_order_ref': 'X',           # ...smuggled alongside
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
        # cross-company store even through the one sanctioned writer.
        # (Odoo's assertRaises helper takes a single class; AccessError and
        # ValidationError both subclass UserError, so UserError catches the
        # check_company refusal and the order-side agreement constraint
        # alike — whichever fires first.)
        with self.assertRaises(UserError):
            other_order.sudo()._shopify_connector_write_projection(
                {'shopify_connector_store_id': self.store.id})
            other_order.flush_recordset()

    def test_projection_store_must_agree_with_the_binding_store(self):
        order = self._order()
        self._bind(order, 'Proj7')
        order.invalidate_recordset()
        self.assertEqual(order.shopify_connector_store_id, self.store)

    def test_same_company_store_drift_is_refused_by_the_order_side(self):
        """P2-1: a same-company store that is NOT the order's binding store is
        refused by the sale.order-side agreement constraint, so drift cannot
        survive even through the one sanctioned writer."""
        order = self._order()
        self._bind(order, 'Proj7b')
        other_store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Projection Same-Co Other Store',
            'shop_domain': 'proj-sameco-other.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            order.sudo()._shopify_connector_write_projection(
                {'shopify_connector_store_id': other_store.id})
            order.flush_recordset()

    def test_a_bindingless_order_cannot_carry_a_store_projection(self):
        """The order-side constraint also refuses a projected store on an
        order that has no Shopify binding at all."""
        order = self._order()
        with self.assertRaises(ValidationError):
            order.sudo()._shopify_connector_write_projection(
                {'shopify_connector_store_id': self.store.id})
            order.flush_recordset()

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


@tagged('post_install', '-at_install')
class TestSaleOrderProjectionRpc(HttpCase):
    """P0-1 request-level regression — the defect and its fix, at the real
    boundary.

    Drives `/web/dataset/call_kw` as an ordinary user who may write sale
    orders (salesman) and read the connector as an Auditor, but holds NO
    connector role that may mutate binding evidence. Every attempt to reach a
    projection column — including one that forges the removed sanction context
    key and one that names the private writer directly — must be refused at
    the wire, with no projection value, binding, order/binding population or
    Store 360 count changing.

    COUNTERFACTUAL: at a1c5931 the projection columns and the private writer
    do not exist, so `write`/`create` accept the forged context key and set
    the columns (the reproduced P0-1), violating every assertion below.
    """

    def setUp(self):
        super().setUp()
        company = self.env.company
        self.store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Projection RPC Store',
            'shop_domain': 'projection-rpc.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })
        self.other_store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Projection RPC Other Store',
            'shop_domain': 'projection-rpc-other.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })
        self.partner = self.env['res.partner'].sudo().create(
            {'name': 'Projection RPC Partner'})
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store.id,
            'sale_domain_enabled': True,
        })
        self.order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'company_id': company.id,
        })
        now = fields.Datetime.now()
        self.binding = self.env[
            'shopify.connector.order.binding'
        ].sudo().create({
            'store_id': self.store.id,
            'sale_order_id': self.order.id,
            'shopify_gid': 'gid://shopify/Order/ProjRpc',
            'shopify_order_name': '#ProjRpc',
            'shopify_financial_status_snapshot': 'PAID',
            'shopify_fulfillment_status_snapshot': 'UNFULFILLED',
            'shopify_updated_at_snapshot': now,
            'shopify_last_evidence_refresh_at': now,
        })
        self.user = self.env['res.users'].sudo().create({
            'name': 'Projection RPC User',
            'login': 'projection_rpc_user',
            'password': 'projection_rpc_user',
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'sales_team.group_sale_salesman_all_leads').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })
        self.env.flush_all()

    def _call_kw(self, model, method, args, kwargs=None):
        return self.make_jsonrpc_request('/web/dataset/call_kw', {
            'model': model,
            'method': method,
            'args': args,
            'kwargs': kwargs or {},
        })

    def _orders_total(self):
        data = self.env['shopify.connector.ui.dashboard'].with_user(
            self.user
        ).get_store_360_data(self.store.id, '30d')
        return (data.get('commercial') or {}).get('orders_total')

    def test_no_client_input_reaches_the_projection_over_rpc(self):
        self.authenticate('projection_rpc_user', 'projection_rpc_user')
        Order = self.env['sale.order'].sudo()
        Binding = self.env['shopify.connector.order.binding'].sudo()

        projection_before = self.order.read(SALE_ORDER_PROJECTION_FIELDS)[0]
        binding_before = self.binding.read([
            'store_id', 'sale_order_id', 'shopify_financial_status_snapshot',
            'sec3_scope_quarantined',
        ])[0]
        orders_total_before = self._orders_total()
        order_count_before = Order.search_count([])
        binding_count_before = Binding.search_count([])

        # 1. lifecycle mirror, forging the removed sanction context key
        with self.assertRaises(JsonRpcException):
            self._call_kw(
                'sale.order', 'write',
                [[self.order.id],
                 {'shopify_connector_financial_status': 'VOIDED'}],
                {'context': {_REMOVED_SANCTION_KEY: True}},
            )
        # 2. the SEC-3 quarantine mirror
        with self.assertRaises(JsonRpcException):
            self._call_kw(
                'sale.order', 'write',
                [[self.order.id], {'shopify_connector_quarantined': True}],
            )
        # 3. reproject onto another SAME-COMPANY store
        with self.assertRaises(JsonRpcException):
            self._call_kw(
                'sale.order', 'write',
                [[self.order.id],
                 {'shopify_connector_store_id': self.other_store.id}],
            )
        # 4. create a sale order carrying projection fields
        with self.assertRaises(JsonRpcException):
            self._call_kw(
                'sale.order', 'create',
                [{'partner_id': self.partner.id,
                  'shopify_connector_store_id': self.store.id,
                  'shopify_connector_financial_status': 'PAID'}],
            )
        # 5. name the private synchronisation writer directly over RPC
        with self.assertRaises(JsonRpcException):
            self._call_kw(
                'sale.order', '_shopify_connector_write_projection',
                [[self.order.id], {'shopify_connector_review': True}],
            )

        self.order.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.order.read(SALE_ORDER_PROJECTION_FIELDS)[0],
            projection_before,
            'no projection value may change over RPC',
        )
        self.assertEqual(
            self.binding.read([
                'store_id', 'sale_order_id',
                'shopify_financial_status_snapshot', 'sec3_scope_quarantined',
            ])[0],
            binding_before,
            'no binding evidence may change',
        )
        self.assertEqual(
            self._orders_total(), orders_total_before,
            'Store 360 orders_total must be unchanged',
        )
        self.assertEqual(
            Order.search_count([]), order_count_before,
            'no sale order (fake Shopify order) may be created',
        )
        self.assertEqual(
            Binding.search_count([]), binding_count_before,
            'no order binding may be created',
        )
