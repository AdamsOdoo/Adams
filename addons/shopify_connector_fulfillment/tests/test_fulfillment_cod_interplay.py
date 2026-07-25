import ast
import uuid
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

# The COD read-model fields owned by the sale order binding (Wave 4 / D-014
# §9.4). The fulfillment domain READS these and never writes them.
COD_READ_MODEL_FIELDS = frozenset((
    'is_cod',
    'cod_commercial_state',
    'cod_fulfillment_state',
    'cod_collection_state',
    'cod_order_value_amount',
    'cod_fulfilled_value_amount',
    'cod_collected_value_amount',
    'cod_refunded_value_amount',
    'cod_cancelled_value_amount',
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
class TestFulfillmentCodInterplay(TransactionCase):
    """COD interplay (D-014 §9.4).

    The fulfillment domain reads the sale-order-binding COD read model and never
    edits it, and it never restores stock from courier evidence -- stock.return.
    picking (Odoo's canonical return path, driven elsewhere) is the only stock-
    restoration path. Full COD-scenario derivation is Wave-4-owned; these focused
    tests assert the read model is readable, that a fulfillment binding can be
    created for a COD order, and (source-level) that no fulfillment production
    code writes cod_* fields or creates a return picking.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.OrderBinding = cls.env['shopify.connector.order.binding']
        cls.Binding = cls.env['shopify.connector.fulfillment.binding']
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
    # Read-model interplay
    # ------------------------------------------------------------------

    def test_cod_read_model_readable_and_binding_creatable(self):
        if 'is_cod' not in self.OrderBinding._fields:
            self.skipTest('Order-binding COD read model absent in this build.')
        order_binding = self.OrderBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': self.sale.id,
            'status': 'active',
            'is_cod': True,
            'cod_fulfillment_state': 'not_dispatched',
        })
        # The read model is readable (the fulfillment domain consumes it).
        self.assertTrue(order_binding.is_cod)
        self.assertEqual(order_binding.cod_fulfillment_state, 'not_dispatched')
        # The remaining COD read-model fields read without error.
        _ = (
            order_binding.cod_commercial_state,
            order_binding.cod_collection_state,
            order_binding.cod_order_value_amount,
        )
        # A fulfillment binding can be created for a COD order.
        binding = self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/COD1',
            'picking_id': self.picking.id,
            'order_binding_id': order_binding.id,
            'status': 'active',
        })
        self.assertTrue(binding.exists())
        self.assertEqual(binding.order_binding_id, order_binding)
        # The fulfillment binding creation left the COD read model unchanged.
        order_binding.invalidate_recordset()
        self.assertTrue(order_binding.is_cod)
        self.assertEqual(order_binding.cod_fulfillment_state, 'not_dispatched')

    # ------------------------------------------------------------------
    # Source-level behavior guards
    # ------------------------------------------------------------------

    def _model_string_constants(self):
        """Yield (filename, str-constant) for every string literal in the
        fulfillment model sources."""
        models_dir = Path(__file__).resolve().parents[1] / 'models'
        for path in sorted(models_dir.glob('*.py')):
            tree = ast.parse(path.read_text('utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    yield path.name, node.value

    def test_no_fulfillment_code_writes_cod_fields(self):
        # cod_* / is_cod are read by attribute access, never referenced as a
        # write/create dict key -- so no such string literal exists at all.
        violations = [
            (name, literal)
            for name, literal in self._model_string_constants()
            if literal in COD_READ_MODEL_FIELDS
        ]
        self.assertFalse(violations, violations)

    def test_fulfillment_never_creates_return_picking(self):
        # stock.return.picking is the ONLY stock-restoration path; the
        # fulfillment domain never creates/validates one from courier evidence.
        violations = [
            (name, literal)
            for name, literal in self._model_string_constants()
            if 'stock.return.picking' in literal
        ]
        self.assertFalse(violations, violations)
