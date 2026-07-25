"""SEC-3 (issue #197) -- two-company isolation matrix for the inventory and
product domains.

Proves the record rules added for `shopify.connector.location.mapping`,
`shopify.connector.inventory.level.binding`,
`shopify.connector.product.template.binding` and
`shopify.connector.product.variant.binding`.

The inventory level binding is the interesting case: it has no company field and
no direct company relation. It reaches company through BOTH parents, so its rule
must require both to be visible -- scoping on one alone leaks the other half of
the pair. `test_read_rule_hides_a_historic_pair_whose_location_is_foreign` and
its product-side twin prove that, and they are the reason the rule is an AND
rather than an OR. `test_write_guard_refuses_a_mixed_company_pair` proves the
primary, write-side protection: such a pair cannot be built through the ORM at
all, because `_check_company_consistency` is an `@api.constrains` and fires even
under `sudo()`.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 `30bde9ff`, read 2026-07-25:
`ir.rule._eval_context` exposes `company_ids` (the multi-company switcher
selection) to a rule domain; `sudo()` bypasses record rules entirely.

No Shopify transport of any kind occurs in this module.
"""

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

CORE = 'shopify_connector_core'


@tagged('post_install', '-at_install')
class TestSec3InventoryCompanyIsolation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'SEC-3 inv company B'})
        # SEC-3 ownership correction (control-room MVP decision, 2026-07-25):
        # a store belongs to exactly ONE company, so each company gets its own
        # store. Binding a company-B location or product to a company-A store is
        # now refused outright by Odoo's `_check_company`.
        cls.store = cls._store('A', cls.company_a)
        cls.store_b = cls._store('B', cls.company_b)
        cls.user_a = cls._role_user('a', cls.company_a)
        cls.user_b = cls._role_user('b', cls.company_b)

        cls.location_a = cls._location('A', cls.company_a)
        cls.location_b = cls._location('B', cls.company_b)
        cls.mapping_a = cls._mapping(cls.store, cls.location_a, 'A')
        cls.mapping_b = cls._mapping(cls.store_b, cls.location_b, 'B')

        cls.template_a, cls.variant_binding_a = cls._product(
            cls.store, 'A', cls.company_a)
        cls.template_b, cls.variant_binding_b = cls._product(
            cls.store_b, 'B', cls.company_b)

    @classmethod
    def _store(cls, tag, company):
        return cls.env['shopify.connector.store'].sudo().create({
            'name': 'SEC-3 inventory store %s' % tag,
            'shop_domain': 'sec3-inventory-%s.myshopify.com' % tag.lower(),
            'api_version': '2026-07',
            'company_id': company.id,
        })

    @classmethod
    def _role_user(cls, label, company):
        return cls.env['res.users'].create({
            'name': 'SEC-3 inv user %s' % label,
            'login': 'sec3_inv_%s' % label,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('%s.group_shopify_connector_admin' % CORE).id,
            ])],
        })

    @classmethod
    def _location(cls, tag, company):
        return cls.env['stock.location'].sudo().create({
            'name': 'SEC-3 loc %s' % tag,
            'usage': 'internal',
            'company_id': company.id,
        })

    @classmethod
    def _mapping(cls, store, location, tag):
        # `with_company` is required, not incidental: the connector's write-side
        # guard `_check_location_company_consistency` fails closed when the
        # mapped location is outside `self.env.company`. Building the company-B
        # fixture in company A's context is refused -- which is the guard
        # working, and is exactly the write-side invariant SEC-3 §4.1 records.
        # These record rules cover the READ side that guard does not reach.
        return cls.env['shopify.connector.location.mapping'].sudo().with_company(
            location.company_id
        ).create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Location/SEC3%s' % tag,
            'odoo_location_id': location.id,
            'match_key': 'manual',
        })

    @classmethod
    def _product(cls, store, tag, company):
        template = cls.env['product.template'].sudo().with_company(company).create({
            'name': 'SEC-3 product %s' % tag,
            'company_id': company.id,
        })
        template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].sudo().with_company(company).create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Product/SEC3%s' % tag,
            'product_template_id': template.id,
        })
        variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].sudo().with_company(company).create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/SEC3%s' % tag,
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })
        return template, variant_binding

    def _pair(self, variant_binding, mapping, tag, company=None, store=None):
        """Create a pair. `company` must match both parents' company.

        `_check_company_consistency` is an `@api.constrains` validation, so it
        fires even under `sudo()`: a pair whose parents disagree on company
        cannot be created through the ORM at all. That is why the mixed-company
        cases below plant their row with SQL instead.
        """
        model = self.env['shopify.connector.inventory.level.binding'].sudo()
        if company is not None:
            model = model.with_company(company)
        return model.create({
            'store_id': (store or self.store).id,
            'product_variant_binding_id': variant_binding.id,
            'location_mapping_id': mapping.id,
            'shopify_inventory_item_gid': 'gid://shopify/InventoryItem/SEC3%s' % tag,
        })

    def _plant_mixed_pair(self, tag, foreign_side):
        """Plant a mixed-company pair with SQL, bypassing the write guard.

        The ORM refuses to build such a row, which is the primary protection.
        This models the *historic record* case #197 asks about: a row that
        predates the guard, or that a future code path creates by mistake. The
        read rule must hide it regardless of how it got there.
        """
        pair = self._pair(
            self.variant_binding_a, self.mapping_a, tag, company=self.company_a,
        )
        column, value = {
            'location': ('location_mapping_id', self.mapping_b.id),
            'product': ('product_variant_binding_id', self.variant_binding_b.id),
            'both': ('location_mapping_id', self.mapping_b.id),
        }[foreign_side]
        self.env.cr.execute(
            'UPDATE shopify_connector_inventory_level_binding '
            'SET %s = %%s WHERE id = %%s' % column, (value, pair.id),
        )
        if foreign_side == 'both':
            self.env.cr.execute(
                'UPDATE shopify_connector_inventory_level_binding '
                'SET product_variant_binding_id = %s WHERE id = %s',
                (self.variant_binding_b.id, pair.id),
            )
        self.env['shopify.connector.inventory.level.binding'].invalidate_model()
        return pair

    def _as(self, user, model):
        return self.env[model].with_user(user)

    # ------------------------------------------------------------------
    # Location mapping
    # ------------------------------------------------------------------

    def test_location_mapping_visible_only_within_its_company(self):
        visible = self._as(self.user_a, 'shopify.connector.location.mapping').search([])
        self.assertIn(
            self.mapping_a.id, visible.ids,
            'company A must still see its own location mapping',
        )
        self.assertNotIn(
            self.mapping_b.id, visible.ids,
            'company A must not see company B location mapping',
        )

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_foreign_location_mapping_direct_read_is_refused(self):
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.location.mapping').browse(
                self.mapping_b.id
            ).read(['shopify_gid'])

    # ------------------------------------------------------------------
    # Product bindings
    # ------------------------------------------------------------------

    def test_product_bindings_visible_only_within_their_company(self):
        templates = self._as(
            self.user_a, 'shopify.connector.product.template.binding'
        ).search([])
        self.assertIn(
            self.variant_binding_a.product_template_binding_id.id, templates.ids)
        self.assertNotIn(
            self.variant_binding_b.product_template_binding_id.id, templates.ids)

        variants = self._as(
            self.user_a, 'shopify.connector.product.variant.binding'
        ).search([])
        self.assertIn(self.variant_binding_a.id, variants.ids)
        self.assertNotIn(self.variant_binding_b.id, variants.ids)

    # ------------------------------------------------------------------
    # Inventory level binding -- the both-parents case
    # ------------------------------------------------------------------

    def test_pair_visible_when_both_parents_are_own_company(self):
        pair = self._pair(
            self.variant_binding_a, self.mapping_a, 'AA', company=self.company_a,
        )
        visible = self._as(
            self.user_a, 'shopify.connector.inventory.level.binding'
        ).search([])
        self.assertIn(
            pair.id, visible.ids,
            'a pair whose product AND location are company A must be visible '
            'to company A -- otherwise the rule is a functional regression',
        )

    def test_pair_hidden_when_both_parents_are_foreign(self):
        pair = self._pair(
            self.variant_binding_b, self.mapping_b, 'BB', company=self.company_b,
            store=self.store_b,
        )
        visible = self._as(
            self.user_a, 'shopify.connector.inventory.level.binding'
        ).search([])
        self.assertNotIn(pair.id, visible.ids)

    def test_write_guard_refuses_a_mixed_company_pair(self):
        """The primary protection: such a pair cannot be built at all.

        `_check_company_consistency` is an `@api.constrains`, so it fires even
        under `sudo()`. This is the write-side half of SEC-3 §4.2.
        """
        with self.assertRaises(UserError):
            self._pair(
                self.variant_binding_a, self.mapping_b, 'AB',
                company=self.company_a,
            )
        with self.assertRaises(UserError):
            self._pair(
                self.variant_binding_b, self.mapping_a, 'BA',
                company=self.company_a,
            )

    def test_read_rule_hides_a_historic_pair_whose_location_is_foreign(self):
        """Defence in depth for the historic records #197 asks about.

        Half-foreign pairs are the reason the rule is an AND, not an OR.
        """
        pair = self._plant_mixed_pair('HISTLOC', 'location')
        visible = self._as(
            self.user_a, 'shopify.connector.inventory.level.binding'
        ).search([])
        self.assertNotIn(
            pair.id, visible.ids,
            'a pair pointing at another company location must not be readable '
            'just because its product is local',
        )

    def test_read_rule_hides_a_historic_pair_whose_product_is_foreign(self):
        pair = self._plant_mixed_pair('HISTPROD', 'product')
        visible = self._as(
            self.user_a, 'shopify.connector.inventory.level.binding'
        ).search([])
        self.assertNotIn(
            pair.id, visible.ids,
            'a pair pointing at another company product must not be readable '
            'just because its location is local',
        )

    # ------------------------------------------------------------------
    # Guards on the audit itself
    # ------------------------------------------------------------------

    def test_system_code_still_sees_every_company(self):
        """sudo() must keep bypassing, or synchronisation breaks."""
        pair = self._pair(
            self.variant_binding_b, self.mapping_b, 'SUDO',
            company=self.company_b, store=self.store_b,
        )
        self.assertIn(
            pair.id,
            self.env['shopify.connector.inventory.level.binding'].sudo().search([]).ids,
        )

    def test_every_company_scoped_inventory_model_has_a_rule(self):
        Rule = self.env['ir.rule'].sudo()
        for model in ('shopify.connector.location.mapping',
                      'shopify.connector.inventory.level.binding',
                      'shopify.connector.product.template.binding',
                      'shopify.connector.product.variant.binding'):
            self.assertTrue(
                Rule.search([('model_id.model', '=', model)]),
                '%s is company-scoped (SEC-3 audit §3.1) and must carry a '
                'record rule' % model,
            )

    def test_control_plane_models_carry_a_fail_closed_company_rule(self):
        """The inverse of the assertion this replaces.

        The superseded version asserted these four models carry NO record rule,
        on the reasoning that the store-scoped control plane is company-neutral.
        That is precisely the gap #197 reported: it left every store,
        credential, job and log cross-readable. Each now carries a fail-closed
        rule, and the domain is checked -- not merely the rule's existence --
        because a rule with the permissive `company_id = False` escape would
        satisfy a presence-only assertion while still leaking every row whose
        owner could not be proven.
        """
        Rule = self.env['ir.rule'].sudo()
        for model in ('shopify.connector.store',
                      'shopify.connector.job',
                      'shopify.connector.job.log',
                      'shopify.connector.store.credential'):
            rules = Rule.search([('model_id.model', '=', model)])
            self.assertTrue(
                rules,
                '%s is store-scoped and must carry a company record rule' % model,
            )
            domains = ' '.join(rules.mapped('domain_force'))
            self.assertIn(
                "('company_id', 'in', company_ids)", domains,
                '%s must be scoped to the reader activated companies' % model,
            )
            self.assertNotIn(
                "('company_id', '=', False)", domains,
                '%s must be FAIL-CLOSED: a row with no provable owner is '
                'visible to nobody, not shared with everybody' % model,
            )
