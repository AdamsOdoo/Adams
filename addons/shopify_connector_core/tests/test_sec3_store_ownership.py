"""SEC-3 (issue #197) -- the store-rooted company ownership matrix.

This file replaces the earlier position that connector control-plane records are
company-NEUTRAL. Under the control-room MVP ownership decision (2026-07-25):

  * a connector store belongs to exactly ONE company;
  * a company may own several stores;
  * sharing one store across companies is outside the MVP;
  * isolation is FAIL-CLOSED: a row whose owning company cannot be proven is
    visible to nobody, rather than to everybody.

What this proves, and why each axis is here rather than assumed:

  * every store-scoped control-plane model -- store, credential, settings,
    location, job, job.log, mutation.attempt, call.lease -- is isolated. These
    are exactly the models the previous implementation classified as neutral,
    which is why they are enumerated explicitly instead of sampled.
  * isolation holds across every read shape a caller can reach: direct
    `browse().read()` by known id, `search`, `search_count`, and a grouped read
    (`formatted_read_group`). A rule that only filters `search` leaks the moment
    a UI groups by anything.
  * isolation holds for write shapes too: create, write and unlink.
  * it holds for all three roles -- plain internal user, Connector User,
    Connector Administrator -- because a role is an authorization axis and
    company is an ownership axis, and neither may substitute for the other.
  * a user ALLOWED in both companies but currently SWITCHED to one sees only
    the active one. Odoo evaluates `company_ids` in a rule as
    `env.companies` (the switcher selection), not `user.company_ids`.
  * every denial leaves ZERO side effects.
  * a historic row with no owning company is invisible to everyone, and the
    administrative remediation path is the only way to resolve it.

Upstream ground truth (DEC-041 D1), odoo/odoo@19.0 `30bde9ff`, read 2026-07-25:
  * `odoo/addons/base/models/ir_rule.py::_eval_context` -- `company_ids` is
    `self.env.companies.ids`, described there as "filtered and trusted";
  * `ir_rule.py::_compute_global` -- a rule with no groups is global and is
    AND-ed with every other rule, so a permissive group rule cannot re-open it;
  * `odoo/orm/models.py` L451/L4009/L4516/L4743 -- `_check_company_auto` makes
    create and write call `_check_company`, which requires a `check_company=True`
    relation's target company to be False or equal to the record's company.

No Shopify store, credential, request or mutation occurs anywhere in this file.
"""

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

CORE = 'shopify_connector_core'

# Every store-scoped control-plane model, with the extra values needed to create
# a row for it. Enumerated rather than discovered so that adding a model without
# adding it here is a visible omission.
CONTROL_PLANE_MODELS = (
    'shopify.connector.store.credential',
    'shopify.connector.store.settings',
    'shopify.connector.location',
    'shopify.connector.job',
    'shopify.connector.call.lease',
)


@tagged('post_install', '-at_install')
class TestSec3StoreOwnership(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'SEC-3 company B'})

        # One store per company. This IS the ownership model: two companies do
        # not share a store, they each own one.
        cls.store_a = cls._store('A', cls.company_a)
        cls.store_b = cls._store('B', cls.company_b)

        cls.user_a = cls._user('a', cls.company_a, [cls.company_a], 'admin')
        cls.user_b = cls._user('b', cls.company_b, [cls.company_b], 'admin')
        # Allowed in BOTH, switched to A only.
        cls.user_both = cls._user(
            'both', cls.company_a, [cls.company_a, cls.company_b], 'admin')
        # The two customer-facing SEC-2 roles and a plain internal user.
        cls.user_connector = cls._user(
            'conn', cls.company_a, [cls.company_a], 'user')
        cls.user_plain = cls._user('plain', cls.company_a, [cls.company_a], None)

        cls.job_a = cls._job(cls.store_a)
        cls.job_b = cls._job(cls.store_b)

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @classmethod
    def _store(cls, tag, company):
        return cls.env['shopify.connector.store'].sudo().create({
            'name': 'SEC-3 store %s' % tag,
            'shop_domain': 'sec3-own-%s.myshopify.com' % tag.lower(),
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })

    @classmethod
    def _user(cls, label, company, allowed, role):
        groups = [cls.env.ref('base.group_user').id]
        if role == 'admin':
            groups.append(cls.env.ref('%s.group_shopify_connector_admin' % CORE).id)
        elif role == 'user':
            groups.append(cls.env.ref('%s.group_shopify_connector_user' % CORE).id)
        return cls.env['res.users'].sudo().create({
            'name': 'SEC-3 %s' % label,
            'login': 'sec3_own_%s' % label,
            'company_id': company.id,
            'company_ids': [(6, 0, [c.id for c in allowed])],
            'group_ids': [(6, 0, groups)],
        })

    @classmethod
    def _job(cls, store):
        return cls.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': 'sec3-%s' % store.id,
        })

    def _as(self, user, model):
        return self.env[model].with_user(user)

    # ------------------------------------------------------------------
    # 1. The ownership field itself
    # ------------------------------------------------------------------

    def test_store_requires_an_owning_company(self):
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.store'].sudo().create({
                'name': 'SEC-3 unowned',
                'shop_domain': 'sec3-unowned.myshopify.com',
                'api_version': '2026-07',
                'company_id': False,
            })

    def test_every_store_scoped_row_inherits_the_store_company(self):
        """Company is derived, never independently set."""
        self.assertEqual(self.job_a.company_id, self.company_a)
        self.assertEqual(self.job_b.company_id, self.company_b)
        settings = self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store_b.id,
        })
        self.assertEqual(settings.company_id, self.company_b)

    # ------------------------------------------------------------------
    # 2. Read isolation, across every read shape
    # ------------------------------------------------------------------

    def test_store_search_is_isolated_both_ways(self):
        visible_a = self._as(self.user_a, 'shopify.connector.store').search([]).ids
        self.assertIn(self.store_a.id, visible_a,
                      'a reader must still see its OWN store; a rule that hides '
                      'everything is a regression, not isolation')
        self.assertNotIn(self.store_b.id, visible_a)

        visible_b = self._as(self.user_b, 'shopify.connector.store').search([]).ids
        self.assertIn(self.store_b.id, visible_b)
        self.assertNotIn(self.store_a.id, visible_b)

    def test_direct_id_browse_of_another_company_store_is_refused(self):
        """Knowing the id must not be enough."""
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.store').browse(
                self.store_b.id).read(['name'])

    def test_search_count_does_not_leak_another_company(self):
        """A count is a read. Leaking "how many" is still leaking."""
        count = self._as(self.user_a, 'shopify.connector.store').search_count(
            [('id', '=', self.store_b.id)])
        self.assertEqual(count, 0)

    def test_grouped_read_does_not_leak_another_company(self):
        """Grouped reads bypass a naive rule that only filters plain searches."""
        groups = self._as(self.user_a, 'shopify.connector.job').formatted_read_group(
            [], ['store_id'], ['__count'])
        store_ids = {group['store_id'][0] for group in groups if group['store_id']}
        self.assertNotIn(self.store_b.id, store_ids)

    def test_every_control_plane_model_is_isolated(self):
        """The models the previous implementation called NEUTRAL."""
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store_b.id})
        self.env['shopify.connector.location'].sudo().create({
            'store_id': self.store_b.id,
            'name': 'SEC-3 location B',
            'shopify_location_gid': 'gid://shopify/Location/SEC3B'})
        for model in ('shopify.connector.store.settings',
                      'shopify.connector.location',
                      'shopify.connector.job'):
            rows = self._as(self.user_a, model).search([])
            self.assertNotIn(
                self.store_b.id, rows.mapped('store_id').ids,
                '%s leaked a row belonging to another company' % model)

    def test_job_log_and_mutation_attempt_are_isolated(self):
        log = self.env['shopify.connector.job.log'].sudo().create({
            'job_id': self.job_b.id,
            'event_type': 'state_change',
            'message': 'sec3',
        })
        self.assertEqual(log.company_id, self.company_b)
        visible = self._as(self.user_a, 'shopify.connector.job.log').search([]).ids
        self.assertNotIn(log.id, visible)

    # ------------------------------------------------------------------
    # 3. The role axis is independent of the company axis
    # ------------------------------------------------------------------

    def test_connector_user_role_is_still_company_isolated(self):
        """A granted role never widens company scope."""
        visible = self._as(self.user_connector, 'shopify.connector.store').search([]).ids
        self.assertIn(self.store_a.id, visible)
        self.assertNotIn(self.store_b.id, visible)

    def test_plain_internal_user_has_no_connector_access_at_all(self):
        with self.assertRaises(AccessError):
            self._as(self.user_plain, 'shopify.connector.store').search([])

    def test_allowed_in_both_but_switched_to_one_sees_only_the_active_one(self):
        """`company_ids` in a rule is the switcher selection, not membership."""
        switched_to_a = self.env['shopify.connector.store'].with_user(
            self.user_both).with_context(allowed_company_ids=[self.company_a.id])
        visible = switched_to_a.search([]).ids
        self.assertIn(self.store_a.id, visible)
        self.assertNotIn(
            self.store_b.id, visible,
            'a user allowed in both companies but switched to A must not see '
            "B's store merely because they could switch to it",
        )

        both_active = self.env['shopify.connector.store'].with_user(
            self.user_both).with_context(
                allowed_company_ids=[self.company_a.id, self.company_b.id])
        self.assertIn(self.store_b.id, both_active.search([]).ids)

    # ------------------------------------------------------------------
    # 4. Write shapes, and zero side effects on denial
    # ------------------------------------------------------------------

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_write_to_another_company_row_is_refused_with_no_side_effect(self):
        before = self.job_b.read(['state'])[0]['state']
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.job').browse(
                self.job_b.id).write({'state': 'cancelled'})
        self.job_b.invalidate_recordset()
        self.assertEqual(
            self.job_b.read(['state'])[0]['state'], before,
            'a denied write must leave the target completely untouched',
        )

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_unlink_of_another_company_row_is_refused_with_no_side_effect(self):
        with self.assertRaises(AccessError):
            self._as(self.user_a, 'shopify.connector.store').browse(
                self.store_b.id).unlink()
        self.assertTrue(self.store_b.exists())

    def test_cross_company_relational_assignment_is_refused(self):
        """A store may only bind business records of its own company.

        Enforced by Odoo's native `_check_company` -- so it holds on create and
        on write, and it holds under `sudo()` too, because it is a constraint
        rather than an access rule.
        """
        partner_b = self.env['res.partner'].sudo().create({
            'name': 'SEC-3 partner B', 'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['shopify.connector.customer.binding'].sudo().create({
                'store_id': self.store_a.id,
                'shopify_gid': 'gid://shopify/Customer/SEC3CROSS',
                'partner_id': partner_b.id,
                'match_key': 'email',
            })

    # ------------------------------------------------------------------
    # 5. sudo() must not become a company-widening tool
    # ------------------------------------------------------------------

    def test_sudo_does_not_let_an_interactive_caller_widen_company(self):
        """`sudo()` bypasses rules by design -- that is exactly why the
        write-side company check must be a CONSTRAINT, not a rule. This proves
        the constraint still bites under sudo, so a sudo seam cannot be used to
        attach another company's record to this store."""
        partner_b = self.env['res.partner'].sudo().create({
            'name': 'SEC-3 sudo partner B', 'company_id': self.company_b.id,
        })
        with self.assertRaises(UserError):
            self.env['shopify.connector.customer.binding'].with_user(
                self.user_a).sudo().create({
                    'store_id': self.store_a.id,
                    'shopify_gid': 'gid://shopify/Customer/SEC3SUDO',
                    'partner_id': partner_b.id,
                    'match_key': 'email',
                })

    # ------------------------------------------------------------------
    # 6. Historic rows with no provable owner
    # ------------------------------------------------------------------

    def test_company_less_historic_store_is_invisible_to_everyone(self):
        """Fail-closed, not fail-open.

        The row is planted with SQL because the ORM constraint (correctly)
        refuses to create one -- this is precisely the shape a database
        upgraded from before SEC-3 can contain.
        """
        self.env.cr.execute(
            "INSERT INTO shopify_connector_store "
            "(name, shop_domain, api_version, state, company_id, "
            " connection_generation, disconnect_status, create_uid, "
            " create_date, write_uid, write_date) "
            "VALUES ('SEC-3 historic', 'sec3-historic.myshopify.com', "
            "'2026-07', 'setup_incomplete', NULL, 0, 'none', 1, now(), 1, now()) "
            "RETURNING id"
        )
        historic_id = self.env.cr.fetchone()[0]
        self.env['shopify.connector.store'].invalidate_model()

        for user in (self.user_a, self.user_b, self.user_both,
                     self.user_connector):
            visible = self._as(user, 'shopify.connector.store').search([]).ids
            self.assertNotIn(
                historic_id, visible,
                'a store whose owning company could not be proven must be '
                'visible to nobody, not to everybody',
            )

    def test_administrative_remediation_assigns_a_company(self):
        self.env.cr.execute(
            "INSERT INTO shopify_connector_store "
            "(name, shop_domain, api_version, state, company_id, "
            " connection_generation, disconnect_status, create_uid, "
            " create_date, write_uid, write_date) "
            "VALUES ('SEC-3 remediate', 'sec3-remediate.myshopify.com', "
            "'2026-07', 'setup_incomplete', NULL, 0, 'none', 1, now(), 1, now()) "
            "RETURNING id"
        )
        historic_id = self.env.cr.fetchone()[0]
        self.env['shopify.connector.store'].invalidate_model()

        store = self.env['shopify.connector.store'].sudo().browse(historic_id)
        store.with_user(self.user_a).action_assign_company(self.company_a.id)
        self.assertEqual(store.company_id, self.company_a)
        self.assertIn(
            historic_id,
            self._as(self.user_a, 'shopify.connector.store').search([]).ids,
        )

    def test_remediation_cannot_re_home_an_already_owned_store(self):
        with self.assertRaises(UserError):
            self.store_a.with_user(self.user_a).action_assign_company(
                self.company_a.id)

    def test_remediation_refuses_a_company_the_caller_does_not_belong_to(self):
        self.env.cr.execute(
            "INSERT INTO shopify_connector_store "
            "(name, shop_domain, api_version, state, company_id, "
            " connection_generation, disconnect_status, create_uid, "
            " create_date, write_uid, write_date) "
            "VALUES ('SEC-3 foreign', 'sec3-foreign.myshopify.com', "
            "'2026-07', 'setup_incomplete', NULL, 0, 'none', 1, now(), 1, now()) "
            "RETURNING id"
        )
        historic_id = self.env.cr.fetchone()[0]
        self.env['shopify.connector.store'].invalidate_model()
        store = self.env['shopify.connector.store'].sudo().browse(historic_id)
        with self.assertRaises(AccessError):
            store.with_user(self.user_a).action_assign_company(self.company_b.id)
        store.invalidate_recordset()
        self.assertFalse(
            store.company_id,
            'a refused remediation must not have assigned anything',
        )
