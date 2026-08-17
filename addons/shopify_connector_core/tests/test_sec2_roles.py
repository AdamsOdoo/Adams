"""SEC-2 (issue #196) -- customer-facing connector roles.

Two layers are proved **separately**, which is the explicit requirement in
issue #196 ("UI visibility and server authorization tested separately"):

* **Layer 1 -- customer-facing visibility.** Exactly two roles are offered on
  the user form (Connector User, Connector Administrator). The four legacy
  capability groups are hidden primitives.
* **Layer 2 -- server authorization.** Authorization still resolves through the
  legacy capability groups via the implied-group closure, reached by direct
  ORM/RPC calls that bypass every UI affordance. A denial must also leave no
  side effect.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 `30bde9ff`, read 2026-07-25:

* ``res.users.all_group_ids = group_ids.all_implied_ids``
  -- ``odoo/addons/base/models/res_users.py`` L447-L449
* ``res.groups.all_implied_ids`` is "the group itself with all its implied
  groups" -- ``odoo/addons/base/models/res_groups.py`` L71-L73
* the user-form privilege selector is built from
  ``res.groups.privilege.group_ids`` -- ``odoo/addons/base/models/res_groups.py``
  L343-L352, so a group without a ``privilege_id`` is not offered there.

No Shopify transport of any kind occurs in this module.
"""

import importlib.util
from pathlib import Path

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.convert import convert_file

CORE = 'shopify_connector_core'

#: The four legacy capability groups, which must remain server-side primitives.
CAPABILITY_GROUPS = (
    'group_shopify_connector_auditor',
    'group_shopify_connector_operator',
    'group_shopify_connector_reviewer',
    'group_shopify_connector_admin',
)

#: The two customer-facing roles SEC-2 introduces.
CUSTOMER_FACING_ROLES = (
    'group_shopify_connector_user',
    'group_shopify_connector_admin',
)


@tagged('post_install', '-at_install')
class TestSec2Roles(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'SEC-2 role store',
            'shop_domain': 'sec2-roles.myshopify.com',
            'api_version': '2026-07',
        })
        cls.privilege = cls.env.ref('%s.privilege_shopify_connector' % CORE)
        cls.role_user = cls._role('user', 'group_shopify_connector_user')
        cls.role_admin = cls._role('admin', 'group_shopify_connector_admin')
        # An ordinary internal employee with no connector role at all.
        cls.plain_user = cls.env['res.users'].create({
            'name': 'SEC-2 plain internal',
            'login': 'sec2_plain_internal',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    @classmethod
    def _role(cls, label, group_xmlid):
        return cls.env['res.users'].create({
            'name': 'SEC-2 %s' % label,
            'login': 'sec2_%s' % label,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('%s.%s' % (CORE, group_xmlid)).id,
            ])],
        })

    def _group(self, xmlid):
        return self.env.ref('%s.%s' % (CORE, xmlid))

    # ------------------------------------------------------------------
    # Layer 1 -- customer-facing visibility
    # ------------------------------------------------------------------

    def test_connector_user_group_exists_with_stable_xmlid(self):
        """U1 gates its visibility on this exact XML ID."""
        group = self.env.ref(
            '%s.group_shopify_connector_user' % CORE, raise_if_not_found=False,
        )
        self.assertTrue(group, 'group_shopify_connector_user must exist')
        self.assertEqual(group.name, 'User')

    def test_privilege_offers_exactly_the_two_customer_facing_roles(self):
        """The user form shows two roles, not the six groups that exist."""
        offered = self.privilege.group_ids
        expected = {self._group(x).id for x in CUSTOMER_FACING_ROLES}
        self.assertEqual(
            set(offered.ids), expected,
            'the Shopify Connector privilege must offer exactly Connector User '
            'and Connector Administrator; offered=%s' % offered.mapped('name'),
        )

    def test_capability_groups_are_hidden_from_the_user_form(self):
        """Auditor/Operator/Reviewer carry no privilege, so are not offered."""
        for xmlid in (
            'group_shopify_connector_auditor',
            'group_shopify_connector_operator',
            'group_shopify_connector_reviewer',
        ):
            group = self._group(xmlid)
            self.assertFalse(
                group.privilege_id,
                '%s must be a hidden capability primitive' % xmlid,
            )

    def test_role_ladder_orders_user_before_administrator(self):
        """Administrator must sit above User in the selector ladder.

        Odoo 19 orders a privilege's groups by how many of that privilege's
        groups each transitively implies (res_groups.py L343-L352), so this
        assertion is what actually drives the on-screen order.
        """
        privilege_groups = self.privilege.group_ids
        user = self._group('group_shopify_connector_user')
        admin = self._group('group_shopify_connector_admin')
        self.assertLess(
            len(user.all_implied_ids & privilege_groups),
            len(admin.all_implied_ids & privilege_groups),
            'Administrator must rank above User in the role ladder',
        )

    # ------------------------------------------------------------------
    # Layer 2 -- implied-group closure (the server-side primitives)
    # ------------------------------------------------------------------

    def test_connector_user_resolves_to_the_expected_capability_closure(self):
        """User resolves only to User, Operator and Auditor."""
        closure = self._group('group_shopify_connector_user').all_implied_ids
        expected = {
            self._group(x).id for x in (
                'group_shopify_connector_user',
                'group_shopify_connector_operator',
                'group_shopify_connector_auditor',
            )
        }
        self.assertEqual(set(closure.ids) & self._connector_group_ids(), expected)
        self.assertNotIn(
            self._group('group_shopify_connector_reviewer').id,
            closure.ids,
            'Connector User must not inherit Reviewer capabilities',
        )

    def test_connector_administrator_resolves_to_all_connector_groups(self):
        """SEC-2 packet §H test 14: admin resolves to all connector groups."""
        closure = self._group('group_shopify_connector_admin').all_implied_ids
        self.assertEqual(
            set(closure.ids) & self._connector_group_ids(),
            self._connector_group_ids(),
        )

    def test_connector_user_does_not_imply_administrator(self):
        """The critical negative: User must never escalate to Administrator."""
        closure = self._group('group_shopify_connector_user').all_implied_ids
        self.assertNotIn(
            self._group('group_shopify_connector_admin').id, closure.ids,
            'Connector User must not imply Connector Administrator',
        )

    def test_role_edges_are_exact_and_upgrade_safe(self):
        """The XML uses replacement semantics, so stale Reviewer edges vanish."""
        user = self._group('group_shopify_connector_user')
        admin = self._group('group_shopify_connector_admin')
        self.assertEqual(
            set(user.implied_ids.ids),
            {self._group('group_shopify_connector_operator').id},
        )
        self.assertEqual(
            set(admin.implied_ids.ids),
            {
                user.id,
                self._group('group_shopify_connector_reviewer').id,
            },
        )

    def test_security_xml_upgrade_removes_historical_user_reviewer_edge(self):
        """Reload the real security XML against a stale pre-upgrade graph.

        The historical edge is deliberately seeded on the actual group record,
        then the module's update data is applied through Odoo's XML loader. This
        proves the ``(6, 0, ...)`` replacement reaches both the group closure
        and an already-existing Connector User, while Administrator retains the
        Reviewer capability. Applying the same update twice proves idempotence.
        """
        user_group = self._group('group_shopify_connector_user')
        admin_group = self._group('group_shopify_connector_admin')
        reviewer = self._group('group_shopify_connector_reviewer')
        operator = self._group('group_shopify_connector_operator')

        # Simulate a database upgraded from the additive User -> Reviewer
        # contract. The existing role user must lose the stale effective edge.
        user_group.write({'implied_ids': [(4, reviewer.id)]})
        self.assertIn(reviewer.id, user_group.implied_ids.ids)
        self.assertTrue(self.role_user.has_group(
            '%s.group_shopify_connector_reviewer' % CORE))

        convert_file(
            self.env, CORE, 'security/shopify_connector_security.xml', None,
            mode='update', noupdate=False,
        )
        self.env.invalidate_all()
        user_group = self._group('group_shopify_connector_user')
        admin_group = self._group('group_shopify_connector_admin')
        self.assertEqual(set(user_group.implied_ids.ids), {operator.id})
        self.assertNotIn(reviewer.id, user_group.all_implied_ids.ids)
        self.assertFalse(self.role_user.has_group(
            '%s.group_shopify_connector_reviewer' % CORE))
        self.assertIn(reviewer.id, admin_group.implied_ids.ids)
        self.assertTrue(self.role_admin.has_group(
            '%s.group_shopify_connector_reviewer' % CORE))

        # Reapplying the same module update must not add edges or otherwise
        # change the exact graph.
        convert_file(
            self.env, CORE, 'security/shopify_connector_security.xml', None,
            mode='update', noupdate=False,
        )
        self.env.invalidate_all()
        self.assertEqual(
            set(self._group('group_shopify_connector_user').implied_ids.ids),
            {operator.id},
        )
        self.assertEqual(
            set(self._group('group_shopify_connector_admin').implied_ids.ids),
            {user_group.id, reviewer.id},
        )

    def test_role_post_migration_is_exact_and_idempotent(self):
        """The versioned upgrade mirrors the XML replacement contract."""
        user = self._group('group_shopify_connector_user')
        admin = self._group('group_shopify_connector_admin')
        operator = self._group('group_shopify_connector_operator')
        reviewer = self._group('group_shopify_connector_reviewer')
        user.write({'implied_ids': [(4, reviewer.id)]})

        path = (
            Path(__file__).resolve().parents[1]
            / 'migrations' / '19.0.1.23.0' / 'post-migrate.py'
        )
        spec = importlib.util.spec_from_file_location(
            'shopify_connector_core_role_post_migrate', path,
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        for _iteration in range(2):
            migration.migrate(self.env.cr, '19.0.1.22.0')
            self.env.invalidate_all()
            self.assertEqual(set(user.implied_ids.ids), {operator.id})
            self.assertEqual(
                set(admin.implied_ids.ids), {user.id, reviewer.id},
            )
            self.assertNotIn(reviewer.id, user.all_implied_ids.ids)

    def test_effective_user_groups_match_the_group_closure(self):
        """Prove the closure on the *user*, not only on the group records."""
        for user, xmlid in (
            (self.role_user, 'group_shopify_connector_user'),
            (self.role_admin, 'group_shopify_connector_admin'),
        ):
            closure = self._group(xmlid).all_implied_ids
            self.assertLessEqual(
                set(closure.ids), set(user.all_group_ids.ids),
                '%s must effectively hold its whole implied closure' % xmlid,
            )

    def test_has_group_resolves_capability_groups_through_the_roles(self):
        """User is routine-only; Administrator retains every capability."""
        for xmlid in ('group_shopify_connector_auditor',
                      'group_shopify_connector_operator'):
            self.assertTrue(
                self.role_user.has_group('%s.%s' % (CORE, xmlid)),
                'Connector User must satisfy has_group(%s)' % xmlid,
            )
            self.assertTrue(
                self.role_admin.has_group('%s.%s' % (CORE, xmlid)),
                'Connector Administrator must satisfy has_group(%s)' % xmlid,
            )
        self.assertFalse(
            self.role_user.has_group(
                '%s.group_shopify_connector_reviewer' % CORE),
            'Connector User must NOT satisfy the reviewer check',
        )
        self.assertTrue(
            self.role_admin.has_group(
                '%s.group_shopify_connector_reviewer' % CORE),
        )
        self.assertFalse(
            self.role_user.has_group(
                '%s.group_shopify_connector_admin' % CORE),
            'Connector User must NOT satisfy the administrator check',
        )
        self.assertTrue(
            self.role_admin.has_group(
                '%s.group_shopify_connector_admin' % CORE),
        )

    def test_plain_internal_user_holds_no_connector_group(self):
        """An employee with no connector role gains nothing from SEC-2."""
        self.assertFalse(
            set(self.plain_user.all_group_ids.ids) & self._connector_group_ids(),
            'a plain internal user must hold no connector capability group',
        )

    def _connector_group_ids(self):
        return {
            self._group(x).id
            for x in CAPABILITY_GROUPS + ('group_shopify_connector_user',)
        }

    # ------------------------------------------------------------------
    # Layer 2 -- direct ORM/RPC authorization, bypassing every UI affordance
    # ------------------------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_plain_internal_user_cannot_read_connector_records_directly(self):
        """No menu, no view -- a raw ORM read must still be refused."""
        with self.assertRaises(AccessError):
            self.env['shopify.connector.store'].with_user(
                self.plain_user
            ).search([('id', '=', self.store.id)])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_connector_user_can_read_but_cannot_write_the_store(self):
        """Store write is administrator-only in the ACL matrix."""
        store = self.env['shopify.connector.store'].with_user(
            self.role_user
        ).browse(self.store.id)
        self.assertEqual(store.name, 'SEC-2 role store')
        before = self.store.name
        with self.assertRaises(AccessError):
            store.write({'name': 'escalated by connector user'})
        self.store.invalidate_recordset(['name'])
        self.assertEqual(
            self.store.name, before,
            'a refused write must leave no side effect',
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_connector_user_cannot_reach_credentials_at_all(self):
        """Credentials are administrator-only; User must not even read them."""
        Credential = self.env['shopify.connector.store.credential']
        with self.assertRaises(AccessError):
            Credential.with_user(self.role_user).search([])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_connector_user_cannot_use_the_mutation_resolution_wizard(self):
        """The administrator-only wizard stays administrator-only."""
        Wizard = self.env['shopify.connector.mutation.resolution.wizard']
        with self.assertRaises(AccessError):
            Wizard.with_user(self.role_user).create({})

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_connector_user_cannot_unlink_connector_records(self):
        """No connector role has unlink on the store."""
        store = self.env['shopify.connector.store'].with_user(
            self.role_user
        ).browse(self.store.id)
        with self.assertRaises(AccessError):
            store.unlink()
        self.assertTrue(
            self.store.exists(), 'a refused unlink must leave the record intact',
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_connector_administrator_can_write_the_store(self):
        """The positive counterpart, so the negatives are not vacuous."""
        store = self.env['shopify.connector.store'].with_user(
            self.role_admin
        ).browse(self.store.id)
        store.write({'name': 'SEC-2 role store (admin edit)'})
        self.store.invalidate_recordset(['name'])
        self.assertEqual(self.store.name, 'SEC-2 role store (admin edit)')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_no_connector_role_escalates_to_odoo_system_administration(self):
        """A connector role must never confer Odoo settings/system rights."""
        for user in (self.role_user, self.role_admin):
            self.assertFalse(
                user.has_group('base.group_system'),
                '%s must not hold Odoo system administration' % user.login,
            )
            self.assertFalse(
                user.has_group('base.group_erp_manager'),
                '%s must not hold Odoo access-rights administration' % user.login,
            )

    # ------------------------------------------------------------------
    # Additivity -- the property that makes this change safe
    # ------------------------------------------------------------------

    def test_capability_groups_keep_their_xml_ids(self):
        """Option M-A forbids renaming or replacing the legacy XML IDs."""
        for xmlid in CAPABILITY_GROUPS:
            self.assertTrue(
                self.env.ref('%s.%s' % (CORE, xmlid), raise_if_not_found=False),
                '%s must still resolve -- SEC-2 is additive, never a rename'
                % xmlid,
            )

    def test_connector_user_grants_no_acl_of_its_own(self):
        """Every right must arrive through the closure, never a direct grant.

        A direct ACL row on the new role would be a second, divergent source of
        truth and would break the "purely additive" property.
        """
        direct = self.env['ir.model.access'].sudo().search([
            ('group_id', '=', self._group('group_shopify_connector_user').id),
        ])
        self.assertFalse(
            direct,
            'group_shopify_connector_user must own no ir.model.access row; '
            'found %s' % direct.mapped('name'),
        )

    def test_capability_group_acls_are_unchanged_in_shape(self):
        """The four primitives still carry the connector ACL matrix."""
        Access = self.env['ir.model.access'].sudo()
        for xmlid in CAPABILITY_GROUPS:
            rows = Access.search([('group_id', '=', self._group(xmlid).id)])
            self.assertTrue(
                rows,
                '%s must still own its ACL rows after SEC-2' % xmlid,
            )
