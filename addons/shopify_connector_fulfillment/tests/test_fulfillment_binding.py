import uuid

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


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
class TestFulfillmentBinding(TransactionCase):
    """D-014-1 fulfillment binding schema.

    Covers:
    - both UNIQUE constraints hold independently:
      UNIQUE(store_id, shopify_gid) and UNIQUE(store_id, picking_id);
    - the backorder chain (DEC-011): two *different* pickings for the same
      order each get their own binding with a distinct **Fulfillment** GID and
      no unique-constraint collision (FO-GID uniqueness would have broken this,
      which is exactly why ``shopify_gid`` is the created Fulfillment GID);
    - binding-field classification is complete, so a sanctioned ``sudo()``
      create succeeds;
    - a non-sudo generic create touching a protected binding field is denied
      with ``AccessError``.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Binding = cls.env['shopify.connector.fulfillment.binding']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'FUL Customer'})
        cls.sale = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.order_binding = cls.env[
            'shopify.connector.order.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id,
            'status': 'active',
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.pt_out = cls.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        # Two distinct outbound pickings for the SAME sale order -> the
        # backorder-chain fixture (each is its own fulfilment event).
        cls.picking_1 = cls._new_picking()
        cls.picking_2 = cls._new_picking()
        # A plain internal (non-superuser) user for the AccessError path: any
        # non-``su`` environment trips the binding-mixin protected-field guard,
        # independent of the user's groups.
        cls.plain_user = cls.env['res.users'].create({
            'name': 'FUL Non-Su',
            'login': 'ful-nonsu-%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    @classmethod
    def _new_picking(cls):
        return cls.env['stock.picking'].create({
            'picking_type_id': cls.pt_out.id,
            'location_id': cls.stock_loc.id,
            'location_dest_id': cls.customer_loc.id,
            'sale_id': cls.sale.id,
        })

    def _binding(self, picking, gid):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })

    def test_field_classification_complete_and_create_succeeds(self):
        # Fail-closed classification must pass: every stored connector field is
        # protected, so nothing is left unclassified and a sudo create works.
        self.Binding._assert_binding_field_classification()
        binding = self._binding(self.picking_1, 'gid://shopify/Fulfillment/1')
        self.assertTrue(binding.id)
        self.assertEqual(binding.store_id, self.store)
        self.assertEqual(binding.picking_id, self.picking_1)
        self.assertEqual(binding.order_binding_id, self.order_binding)

    @mute_logger('odoo.sql_db')
    def test_unique_store_fulfillment_gid(self):
        # First binding: picking_1 with a given Fulfillment GID.
        self._binding(self.picking_1, 'gid://shopify/Fulfillment/DUP')
        # A *different* picking with the SAME Fulfillment GID still collides on
        # UNIQUE(store_id, shopify_gid).
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._binding(self.picking_2, 'gid://shopify/Fulfillment/DUP')

    @mute_logger('odoo.sql_db')
    def test_unique_store_picking(self):
        # First binding: picking_1 with a given Fulfillment GID.
        self._binding(self.picking_1, 'gid://shopify/Fulfillment/A')
        # The SAME picking with a *different* Fulfillment GID still collides on
        # UNIQUE(store_id, picking_id): one picking is one fulfilment event.
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._binding(self.picking_1, 'gid://shopify/Fulfillment/B')

    def test_backorder_chain_no_collision(self):
        # DEC-011: a backorder chain fulfils one order through several pickings.
        # Two different pickings for the SAME order each get their own binding
        # with a distinct Fulfillment GID -> no unique-constraint collision.
        b1 = self._binding(self.picking_1, 'gid://shopify/Fulfillment/BO-1')
        b2 = self._binding(self.picking_2, 'gid://shopify/Fulfillment/BO-2')
        self.assertNotEqual(b1.id, b2.id)
        self.assertNotEqual(b1.shopify_gid, b2.shopify_gid)
        self.assertNotEqual(b1.picking_id, b2.picking_id)
        # Same order binding -> the chain fulfils a single order.
        self.assertEqual(b1.order_binding_id, b2.order_binding_id)

    def test_non_sudo_create_of_protected_field_raises(self):
        # Every required binding field is protected; a generic (non-su) create
        # is refused before any row is written.
        with self.assertRaises(AccessError):
            self.Binding.with_user(self.plain_user).create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Fulfillment/NoSudo',
                'picking_id': self.picking_2.id,
                'order_binding_id': self.order_binding.id,
            })
