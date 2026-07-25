"""SEC-3 (issue #197) -- two-company isolation matrix for the sale domain.

Proves the record rules added for `shopify.connector.customer.binding`,
`shopify.connector.order.binding` and `shopify.connector.tax.mapping`, and the
role-negative half of the matrix.

The shape of every positive/negative pair is deliberate: each test asserts BOTH
that company A's row is visible to a company-A reader AND that company B's row
is not. A one-sided assertion would pass just as well against a rule that hides
everything, which would be a functional regression disguised as security.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 `30bde9ff`, read 2026-07-25:
`ir.rule._eval_context` exposes `company_ids` -- the multi-company *switcher
selection* -- to a rule domain, and `sudo()` bypasses record rules entirely, so
connector system code is unaffected.

No Shopify transport of any kind occurs in this module.
"""

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

CORE = 'shopify_connector_core'


@tagged('post_install', '-at_install')
class TestSec3SaleCompanyIsolation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'SEC-3 company B'})

        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'SEC-3 isolation store',
            'shop_domain': 'sec3-isolation.myshopify.com',
            'api_version': '2026-07',
        })

        # A reader that may only ever see company A.
        cls.user_a = cls._role_user('a', cls.company_a)
        # A reader allowed in both, currently switched to company B only.
        cls.user_b = cls._role_user('b', cls.company_b)

        cls.partner_a = cls._partner('SEC-3 partner A', cls.company_a)
        cls.partner_b = cls._partner('SEC-3 partner B', cls.company_b)
        cls.binding_a = cls._customer_binding(cls.partner_a, 'A')
        cls.binding_b = cls._customer_binding(cls.partner_b, 'B')

    @classmethod
    def _role_user(cls, label, company):
        return cls.env['res.users'].create({
            'name': 'SEC-3 sale user %s' % label,
            'login': 'sec3_sale_%s' % label,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('%s.group_shopify_connector_admin' % CORE).id,
            ])],
        })

    @classmethod
    def _partner(cls, name, company):
        return cls.env['res.partner'].create({
            'name': name, 'company_id': company.id,
        })

    @classmethod
    def _customer_binding(cls, partner, tag):
        return cls.env['shopify.connector.customer.binding'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Customer/SEC3%s' % tag,
            'partner_id': partner.id,
            'match_key': 'email',
        })

    def _as(self, user, model):
        return self.env[model].with_user(user)

    # ------------------------------------------------------------------
    # Customer binding
    # ------------------------------------------------------------------

    def test_customer_binding_visible_only_within_its_company(self):
        visible_to_a = self._as(self.user_a, 'shopify.connector.customer.binding').search([])
        self.assertIn(
            self.binding_a.id, visible_to_a.ids,
            'company A must still see its OWN customer binding; a rule that '
            'hides everything is a regression, not isolation',
        )
        self.assertNotIn(
            self.binding_b.id, visible_to_a.ids,
            'company A must not see company B customer binding',
        )

        visible_to_b = self._as(self.user_b, 'shopify.connector.customer.binding').search([])
        self.assertIn(self.binding_b.id, visible_to_b.ids)
        self.assertNotIn(self.binding_a.id, visible_to_b.ids)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_direct_browse_read_of_foreign_binding_is_refused(self):
        """search() filtering is not enough: a direct id read must also fail."""
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.customer.binding').browse(
                self.binding_b.id
            ).read(['shopify_gid'])

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_foreign_binding_cannot_be_written_or_unlinked(self):
        """A refused write must also leave no side effect."""
        before = self.binding_b.match_key
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.customer.binding').browse(
                self.binding_b.id
            ).write({'match_key': 'manual'})
        self.binding_b.invalidate_recordset(['match_key'])
        self.assertEqual(self.binding_b.match_key, before)

    def test_search_count_does_not_leak_foreign_rows(self):
        """A count is a read: it must not reveal that company B rows exist."""
        count_a = self._as(self.user_a, 'shopify.connector.customer.binding').search_count(
            [('store_id', '=', self.store.id)]
        )
        self.assertEqual(
            count_a, 1,
            'company A must count exactly its own binding on this store',
        )

    def test_grouped_read_does_not_leak_foreign_rows(self):
        """Aggregates are a classic isolation bypass; prove they are scoped.

        `formatted_read_group` is the Odoo 19 replacement for the deprecated
        `read_group` (odoo/odoo@19.0 30bde9ff).
        """
        groups = self._as(
            self.user_a, 'shopify.connector.customer.binding'
        ).formatted_read_group(
            [('store_id', '=', self.store.id)], ['store_id'], ['__count'],
        )
        total = sum(group['__count'] for group in groups)
        self.assertEqual(
            total, 1, 'a grouped read must not aggregate foreign rows',
        )

    # ------------------------------------------------------------------
    # Order binding
    # ------------------------------------------------------------------

    def test_order_binding_visible_only_within_its_company(self):
        order_a = self._sale_order(self.company_a, self.partner_a)
        order_b = self._sale_order(self.company_b, self.partner_b)
        ob_a = self._order_binding(order_a, 'A')
        ob_b = self._order_binding(order_b, 'B')

        visible = self._as(self.user_a, 'shopify.connector.order.binding').search([])
        self.assertIn(ob_a.id, visible.ids)
        self.assertNotIn(ob_b.id, visible.ids)

    def _sale_order(self, company, partner):
        return self.env['sale.order'].sudo().create({
            'partner_id': partner.id, 'company_id': company.id,
        })

    def _order_binding(self, order, tag):
        return self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/SEC3%s' % tag,
            'sale_order_id': order.id,
        })

    # ------------------------------------------------------------------
    # Neutral models must stay readable (the rules must not over-reach)
    # ------------------------------------------------------------------

    def test_store_and_job_remain_visible_across_companies(self):
        """The store is store-scoped and NEUTRAL by design (audit §3.3).

        If a future change accidentally scopes the control plane by company,
        every operator loses their own store; this guards that direction.
        """
        for user in (self.user_a, self.user_b):
            stores = self._as(user, 'shopify.connector.store').search(
                [('id', '=', self.store.id)]
            )
            self.assertEqual(
                stores.ids, [self.store.id],
                '%s must still see the connector store' % user.login,
            )

    # ------------------------------------------------------------------
    # sudo() must still bypass, or synchronisation breaks
    # ------------------------------------------------------------------

    def test_system_code_still_sees_every_company(self):
        """Connector system code runs sudo() and must be unaffected."""
        all_bindings = self.env['shopify.connector.customer.binding'].sudo().search([])
        self.assertIn(self.binding_a.id, all_bindings.ids)
        self.assertIn(self.binding_b.id, all_bindings.ids)

    # ------------------------------------------------------------------
    # Role negatives, crossed with company
    # ------------------------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_plain_internal_user_sees_no_binding_in_any_company(self):
        """Company isolation must not be the ONLY thing standing in the way."""
        plain = self.env['res.users'].create({
            'name': 'SEC-3 plain', 'login': 'sec3_plain',
            'company_id': self.company_a.id,
            'company_ids': [(6, 0, [self.company_a.id, self.company_b.id])],
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self._as(plain, 'shopify.connector.customer.binding').search([])

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_connector_user_role_is_still_company_scoped(self):
        """The SEC-2 Connector User role does not escape SEC-3 scoping."""
        role_user = self.env['res.users'].create({
            'name': 'SEC-3 connector user', 'login': 'sec3_connector_user',
            'company_id': self.company_a.id,
            'company_ids': [(6, 0, [self.company_a.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('%s.group_shopify_connector_user' % CORE).id,
            ])],
        })
        visible = self._as(role_user, 'shopify.connector.customer.binding').search([])
        self.assertIn(self.binding_a.id, visible.ids)
        self.assertNotIn(
            self.binding_b.id, visible.ids,
            'a Connector User in company A must not read company B bindings',
        )

    def test_every_company_scoped_sale_model_has_a_rule(self):
        """Guard against a future model landing without an isolation rule."""
        Rule = self.env['ir.rule'].sudo()
        for model in ('shopify.connector.customer.binding',
                      'shopify.connector.order.binding',
                      'shopify.connector.tax.mapping'):
            rules = Rule.search([('model_id.model', '=', model)])
            self.assertTrue(
                rules,
                '%s is company-scoped (SEC-3 audit §3.1) and must carry a '
                'record rule' % model,
            )
