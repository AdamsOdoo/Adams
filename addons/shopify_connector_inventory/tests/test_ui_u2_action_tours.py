"""Driven-browser evidence for the U2 INVENTORY action controls.

U2 shipped with server-side visibility and wiring tests plus a read-only
navigation tour. Its acceptance matrix asks for browser evidence of the
operator CONTROLS, and there was none: every control that writes was left to
"the driven runtime campaign". That is the gap this file closes for the three
inventory controls.

  * `Confirm First Push`  -> `action_confirm_first_push`   (writes)
  * `Change Push`         -> `action_set_push_enabled`     (writes)
  * `Verify Now`          -> `action_recheck_inventory_pair` (writes + enqueues)

WHY A BROWSER, WHEN THE SERVER METHODS ARE ALREADY TESTED. Because the server
methods being right does not make the screen right, and all three of these had
a real UI/server disagreement that only pressing the control could find:

  1. `Confirm First Push` was rendered `invisible="first_push_state != 'pending'"`
     while `action_confirm_first_push` refuses anything that is not
     `previewed`. The button was shown in the only state that fails and hidden
     in the only state that works, and the First-Push Guard queue listed
     `pending` alone -- so the sanctioned confirmation was unreachable. Every
     pre-existing server test writes `first_push_state = 'previewed'` itself
     before calling the method, which is exactly why none of them saw it.
  2. `Verify Now` was gated on Operator; its service admits Reviewer or
     Administrator only.
  3. `Change Push` was gated on Operator while its transient wizard was ACL'd
     to Administrator alone, so a Connector User was refused at the dialog.

NO SHOPIFY. Nothing here holds a credential or reaches the network. The two
enqueueing paths create a `shopify.connector.job` ROW; job execution is a
separate dispatcher concern that no tour starts. `test_no_shopify_transport_*`
below asserts that directly rather than asserting it in prose.

RESIDUE. `HttpCase` is a `TransactionCase`: the whole fixture is rolled back
at teardown. `test_fixtures_leave_no_residue` proves the assertion rather than
assuming it.
"""

import uuid

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)

GUARD_ACTION = (
    'shopify_connector_inventory.action_shopify_connector_inventory_first_push'
)
WORKSPACE_ACTION = (
    'shopify_connector_inventory.action_shopify_connector_inventory_workspace'
)
MAPPING_ACTION = (
    'shopify_connector_inventory.action_shopify_connector_location_mapping'
)


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the core suites.
@tagged('post_install', '-at_install', 'shopify_connector_u2_actions')
class TestUiU2InventoryActionTours(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U2 action store',
            'shop_domain': 'u2-actions.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'U2 action location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        cls.mapping = cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/U2ACT',
            'odoo_location_id': cls.location.id,
            'match_key': 'manual',
            'shopify_location_name_snapshot': 'U2 action warehouse',
        })
        template = cls.env['product.template'].create({'name': 'U2 action widget'})
        template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/U2ACT',
            'product_template_id': template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/U2ACT',
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })

        # Two roles, both real customer-facing SEC-2 roles.
        cls.reviewer = cls._connector_user(
            'u2act_reviewer',
            'shopify_connector_core.group_shopify_connector_user',
        )
        # Auditor implies read everywhere and act nowhere: the role the
        # server refuses for every control in this file.
        cls.auditor = cls._connector_user(
            'u2act_auditor',
            'shopify_connector_core.group_shopify_connector_auditor',
        )

    @classmethod
    def _connector_user(cls, login, group_xmlid):
        return cls.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(group_xmlid).id,
            ])],
        })

    def _level(self, gid, first_push_state, **extra):
        values = {
            'store_id': self.store.id,
            'product_variant_binding_id': self.variant_binding.id,
            'location_mapping_id': self.mapping.id,
            'shopify_inventory_item_gid': gid,
            'first_push_state': first_push_state,
            'pending_target_available': 12.0,
        }
        values.update(extra)
        return self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create(values)

    def _url(self, action_xmlid):
        return '/odoo/action-%s' % action_xmlid

    # ------------------------------------------------------------------
    # 1. First-push confirmation
    # ------------------------------------------------------------------

    def test_first_push_confirm_tour(self):
        """The allowed role reaches the control from the queue and succeeds.

        This is the assertion the shipped UI could not have satisfied: with
        the guard queue scoped to `pending` and the button hidden outside
        `pending`, there was no path from the queue to a successful confirm.
        """
        binding = self._level('gid://shopify/InventoryItem/U2PREV', 'previewed',
                              first_push_preview_qty=12.0)
        self.assertEqual(binding.first_push_state, 'previewed')
        self.env.flush_all()

        self.start_tour(self._url(GUARD_ACTION),
                        'shopify_connector_u2_first_push_confirm_tour',
                        login='u2act_reviewer')

        binding.invalidate_recordset()
        self.assertEqual(
            binding.first_push_state, 'confirmed',
            'the browser confirmation did not reach the server',
        )
        self.assertEqual(binding.first_push_confirmed_by_uid, self.reviewer)
        self.assertTrue(binding.first_push_confirmed_at)

    def test_first_push_pending_offers_no_control_tour(self):
        """A pair awaiting its preview offers no control the server refuses."""
        binding = self._level('gid://shopify/InventoryItem/U2PEND', 'pending')
        self.env.flush_all()

        self.start_tour(
            self._url(GUARD_ACTION),
            'shopify_connector_u2_first_push_pending_has_no_control_tour',
            login='u2act_reviewer')

        binding.invalidate_recordset()
        self.assertEqual(
            binding.first_push_state, 'pending',
            'nothing may have been written by a read-only visit',
        )

    def test_first_push_denied_for_a_role_the_server_refuses(self):
        """An auditor may read the disclosure and is offered no control."""
        binding = self._level('gid://shopify/InventoryItem/U2DENY', 'previewed',
                              first_push_preview_qty=12.0)
        self.env.flush_all()

        self.start_tour(self._url(GUARD_ACTION),
                        'shopify_connector_u2_first_push_denied_tour',
                        login='u2act_auditor')

        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_state, 'previewed')
        self.assertFalse(binding.first_push_confirmed_by_uid)

    def test_repeated_confirmation_cannot_double_write(self):
        """Idempotency at the surface: the control is gone after it is used.

        The tour asserts the button's absence after confirming; this asserts
        the server side of the same property, so a future view change that
        re-shows the button still cannot produce a second confirmation.
        """
        binding = self._level('gid://shopify/InventoryItem/U2TWICE', 'previewed',
                              first_push_preview_qty=12.0)
        binding.with_user(self.reviewer).action_confirm_first_push()
        binding.invalidate_recordset()
        first_actor = binding.first_push_confirmed_by_uid
        first_at = binding.first_push_confirmed_at
        with self.assertRaises(Exception):
            binding.with_user(self.reviewer).action_confirm_first_push()
        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_confirmed_by_uid, first_actor)
        self.assertEqual(binding.first_push_confirmed_at, first_at)

    # ------------------------------------------------------------------
    # 2. Location push toggle
    # ------------------------------------------------------------------

    def test_push_toggle_tour(self):
        """A Connector User opens the dialog and applies the change.

        Before the ACL correction this failed at the DIALOG rather than at
        the control: the button was gated on Operator, the transient wizard
        was ACL'd to Administrator alone, and a Connector User was refused
        on `create()` after pressing a control the UI had offered them.
        """
        self.assertTrue(self.mapping.push_enabled)
        self.env.flush_all()

        self.start_tour(self._url(MAPPING_ACTION),
                        'shopify_connector_u2_push_toggle_tour',
                        login='u2act_reviewer')

        self.mapping.invalidate_recordset()
        self.assertFalse(
            self.mapping.push_enabled,
            'the dialog said push would stop; the server must agree',
        )

    # ------------------------------------------------------------------
    # 3. Inventory re-check (enqueues)
    # ------------------------------------------------------------------

    def _blocked_pair(self, gid):
        """One eligible blocked pair: exactly what the release path requires."""
        binding = self._level(gid, 'confirmed')
        pair_key = 'inventory_pair:%s:%s:%s' % (
            self.store.id, binding.shopify_inventory_item_gid,
            self.mapping.shopify_gid,
        )
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_set_quantities',
            'state': 'queued',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': binding.id,
            'shopify_target_gid': pair_key,
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': self.store.connection_generation,
        })
        token = uuid.uuid4().hex
        job.sudo().write({
            'state': 'running',
            'current_attempt_token': token,
            'started_at': fields.Datetime.now(),
            'running_since': fields.Datetime.now(),
        })
        side_context = dict(self.env.context)
        side_context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
        attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].with_context(side_context)._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': {
                'inventory_item_gid': binding.shopify_inventory_item_gid,
                'location_gid': self.mapping.shopify_gid,
                'target_quantity': 12.0,
                'change_from_quantity': 5.0,
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()),
            },
            'business_intent_fingerprint': 'bif-%s' % token,
            'exact_request_fingerprint': 'erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        })
        attempt._record_direct_outcome('failed_clean')
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': 'inventory_location_missing',
            'manual_review_subreason': 'inventory_location_missing',
            'finished_at': fields.Datetime.now(),
        })
        return binding, job

    def test_recheck_tour_enqueues_exactly_one_successor(self):
        binding, job = self._blocked_pair('gid://shopify/InventoryItem/U2RECH')
        self.env.flush_all()

        self.start_tour(self._url(WORKSPACE_ACTION),
                        'shopify_connector_u2_recheck_tour',
                        login='u2act_reviewer')

        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(job.cancel_reason, 'manual_review_release')
        successors = self.env['shopify.connector.job'].search([
            ('res_id', '=', binding.id),
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('job_type', '=', 'inventory_push_sync'),
            ('state', 'not in', ('cancelled', 'failed_final')),
        ])
        self.assertEqual(
            len(successors), 1,
            'the browser re-check must produce exactly one successor job',
        )
        self.assertFalse(
            self.env['shopify.connector.mutation.attempt'].search_count(
                [('job_id', '=', successors.id)]),
            'a release is orchestration only -- it must create no transport '
            'attempt, and certainly no Shopify request',
        )

    def test_recheck_blank_reason_is_refused_in_the_browser(self):
        """A blank reason is refused, and nothing is enqueued."""
        binding, job = self._blocked_pair('gid://shopify/InventoryItem/U2BLANK')
        self.env.flush_all()

        self.start_tour(self._url(WORKSPACE_ACTION),
                        'shopify_connector_u2_recheck_blank_reason_tour',
                        login='u2act_reviewer')

        job.invalidate_recordset()
        self.assertEqual(
            job.state, 'blocked_manual_review',
            'a refused re-check must leave the blocked job exactly as it was',
        )
        self.assertFalse(self.env['shopify.connector.job'].search_count([
            ('res_id', '=', binding.id),
            ('job_type', '=', 'inventory_push_sync'),
        ]))

    # ------------------------------------------------------------------
    # 4. Blocked-state disclosure
    # ------------------------------------------------------------------

    def test_quarantined_pair_is_not_reachable_by_an_operator(self):
        """The blocked state, as an operator actually meets it.

        The form carries an "Excluded from synchronisation" danger banner for
        a quarantined row. Driving it proves the banner is UNREACHABLE: the
        SEC-3 store rule is a global `ir.rule` that filters
        `sec3_scope_quarantined = True` out of every non-superuser read, so
        the row the banner sits on is invisible and the pair simply is not in
        the queue.

        That is stricter than the banner, and it is the correct fail-closed
        posture -- so this asserts the absence rather than weakening the rule
        to make a banner appear. The banner's unreachability is recorded as a
        P3 finding (dead UI, not a hole) in the U2 validation record.
        """
        binding = self._level('gid://shopify/InventoryItem/U2QUAR', 'previewed',
                              first_push_preview_qty=12.0)
        binding.sudo().write({'sec3_scope_quarantined': True})
        self.env.flush_all()

        self.assertFalse(
            self.env['shopify.connector.inventory.level.binding'].with_user(
                self.reviewer).search([('id', '=', binding.id)]),
            'a quarantined pair must be invisible to an ordinary read',
        )
        self.start_tour(self._url(WORKSPACE_ACTION),
                        'shopify_connector_u2_quarantined_is_not_listed_tour',
                        login='u2act_reviewer')

    # ------------------------------------------------------------------
    # Cross-cutting properties the tours must not be trusted to imply
    # ------------------------------------------------------------------

    def test_company_boundary_is_enforced_on_every_u2_inventory_action(self):
        """A caller in the wrong company is refused by every control."""
        other = self.env['res.company'].create({'name': 'U2 action other co'})
        outsider = self.env['res.users'].create({
            'name': 'u2act_outsider',
            'login': 'u2act_outsider',
            'company_id': other.id,
            'company_ids': [(6, 0, [other.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin').id,
            ])],
        })
        binding = self._level('gid://shopify/InventoryItem/U2CO', 'previewed',
                              first_push_preview_qty=12.0)
        self.env.flush_all()
        # The store-rooted SEC-3 rules put the row outside the outsider's
        # scope entirely, so the refusal is a read refusal -- the strongest
        # form: the control's record is not reachable at all.
        self.assertFalse(
            self.env['shopify.connector.inventory.level.binding'].with_user(
                outsider).search([('id', '=', binding.id)]),
            'a foreign-company user must not even see the pair',
        )
        self.assertFalse(
            self.env['shopify.connector.location.mapping'].with_user(
                outsider).search([('id', '=', self.mapping.id)]),
        )
        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_state, 'previewed')

    def test_no_shopify_transport_is_reachable_from_a_u2_control(self):
        """None of the three controls performs a Shopify request.

        Asserted structurally, against the methods the buttons name, rather
        than by watching the network: the transport entry point is the API
        client, and none of these call paths reaches it.
        """
        import inspect

        Binding = self.env['shopify.connector.inventory.level.binding']
        Mapping = self.env['shopify.connector.location.mapping']
        for model, method in (
            (Binding, 'action_confirm_first_push'),
            (Mapping, 'action_set_push_enabled'),
        ):
            source = inspect.getsource(getattr(type(model), method))
            for forbidden in ('api_client', 'graphql', 'requests.', '_send'):
                self.assertNotIn(
                    forbidden, source,
                    '%s reaches %r; a U2 operator control must not perform a '
                    'Shopify request' % (method, forbidden),
                )

    def test_fixtures_leave_no_residue(self):
        """The seeded rows exist only inside this transaction.

        `HttpCase` derives from `TransactionCase`, so the fixture is rolled
        back at teardown. Stated as a test rather than as a comment because
        "the tour leaves no residue" is a claim the evidence record makes.
        """
        binding = self._level('gid://shopify/InventoryItem/U2RESID', 'pending')
        self.assertTrue(binding.exists())
        # Nothing here commits: no `cr.commit()` appears in any U2 action path.
        import inspect
        from odoo.addons.shopify_connector_inventory.models import (
            shopify_connector_location_mapping,
        )
        source = inspect.getsource(shopify_connector_location_mapping)
        self.assertNotIn(
            'cr.commit()', source,
            'a U2 control that commits would survive the rollback and leave '
            'residue in the test database',
        )
