"""Driven-browser evidence for the U2 ORDER action control.

The one sanctioned operator control on the U2 order-review and COD surfaces is
`Approve Payment`, which opens the manual-gateway approval dialog and delegates
to `action_approve_manual_gateway_order`. It writes the approval provenance AND
enqueues a read-only evidence-refresh job, so it is the U2 control with the
widest blast radius -- and it had no driven-browser evidence at all: the U2
navigation tour is read-only by construction and never presses it.

COD is the SAME surface. `action_shopify_connector_cod_reconciliation` reuses
`shopify.connector.order.binding` and the same S17 form, and the COD list
carries no `<button>` of its own, so the COD workspace's only action control is
this one. `test_cod_surface_offers_no_separate_write_control` pins that, so a
reader of the copy deck cannot mistake the COD ledger for something editable.

WHAT THE BROWSER ADDS OVER THE SERVER TESTS. The approval path is already
well covered server-side (permissions, reason provenance, redaction,
idempotency, atomic rollback). None of that proves the operator can reach it:
that the warning is rendered above the control rather than below it, that the
dialog states what approving does and does not do, that the control takes
keyboard focus and shows a focus ring, and that a role the server refuses is
not shown the control in the first place.

NO SHOPIFY. The approval enqueues a `shopify.connector.job` ROW. Nothing here
holds a credential or reaches the network, and no dispatcher runs.
"""

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .test_order_import_mapping import OrderImportCase

WORKSPACE_ACTION = (
    'shopify_connector_sale.action_shopify_connector_order_workspace'
)
COD_ACTION = (
    'shopify_connector_sale.action_shopify_connector_cod_reconciliation'
)


@tagged('post_install', '-at_install', 'shopify_connector_u2_actions')
class TestUiU2SaleActionTours(OrderImportCase, HttpCase):
    """`OrderImportCase` brings the network-free order fixture substrate;
    `HttpCase` brings the browser. Both derive from `TransactionCase`, so the
    whole fixture is rolled back at teardown and leaves no residue."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reviewer = cls._u2_user(
            'u2ord_reviewer',
            'shopify_connector_core.group_shopify_connector_user',
        )
        # Auditor reads everything and acts on nothing: the role
        # `action_approve_manual_gateway_order` refuses.
        cls.auditor = cls._u2_user(
            'u2ord_auditor',
            'shopify_connector_core.group_shopify_connector_auditor',
        )

    @classmethod
    def _u2_user(cls, login, group_xmlid):
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

    def _pending_approval_binding(self, gid):
        """One imported COD order sitting in `pending` approval."""
        self.settings.write({
            'manual_gateway_policy': 'require_approval',
            'approved_manual_gateways': 'Cash on Delivery',
            'order_confirmation_policy': 'paid_only',
        })
        payload = self._payload(gid, 'PENDING')
        payload['paymentGatewayNames'] = ['Cash on Delivery']
        payload['transactions'] = [self._transaction(
            gateway='Cash on Delivery', manual=True,
        )]
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.manual_gateway_approval_state, 'pending')
        self.assertTrue(binding.is_cod)
        return binding

    def _url(self, action_xmlid):
        return '/odoo/action-%s' % action_xmlid

    # ------------------------------------------------------------------
    # The action control
    # ------------------------------------------------------------------

    def test_order_approval_tour(self):
        """The allowed role reads the disclosure, then approves by dialog."""
        binding = self._pending_approval_binding('gid://shopify/Order/U2ACT')
        # Counted by TYPE, not in total: approving enqueues the evidence
        # refresh AND a separate lifecycle audit job
        # (`_create_lifecycle_audit_job`). Asserting a total of one would
        # simply be wrong, and would have to be "fixed" by loosening it later.
        refresh_before = self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
        ])
        self.env.flush_all()

        self.start_tour(self._url(WORKSPACE_ACTION),
                        'shopify_connector_u2_order_approval_tour',
                        login='u2ord_reviewer')

        binding.invalidate_recordset()
        self.assertEqual(
            binding.manual_gateway_approval_state, 'pending',
            'the approval records provenance and stays `pending` until the '
            'evidence refresh confirms it -- the browser must not change that',
        )
        self.assertEqual(binding.manual_gateway_approved_by_uid, self.reviewer)
        self.assertTrue(binding.manual_gateway_approved_at)

        refresh_after = self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
        ])
        self.assertEqual(
            refresh_after, refresh_before + 1,
            'approving must enqueue exactly one evidence-refresh job',
        )

    def test_order_approval_denied_for_a_role_the_server_refuses(self):
        """An auditor reads the disclosure and is offered no control."""
        binding = self._pending_approval_binding('gid://shopify/Order/U2DENY')
        self.env.flush_all()

        self.start_tour(self._url(WORKSPACE_ACTION),
                        'shopify_connector_u2_order_approval_denied_tour',
                        login='u2ord_auditor')

        binding.invalidate_recordset()
        self.assertFalse(binding.manual_gateway_approved_by_uid)
        self.assertFalse(binding.manual_gateway_approved_at)

    def test_repeated_approval_enqueues_no_second_job(self):
        """Idempotency: pressing the control twice must not double-enqueue.

        The tour cannot press a control twice in one run without racing the
        dialog, so the property is asserted directly against the method the
        dialog delegates to -- the same method, same user, same record.
        """
        binding = self._pending_approval_binding('gid://shopify/Order/U2TWICE')
        binding.with_user(self.reviewer).action_approve_manual_gateway_order(
            'First approval.')
        after_first = self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
        ])
        binding.invalidate_recordset()
        actor, at = (binding.manual_gateway_approved_by_uid,
                     binding.manual_gateway_approved_at)

        binding.with_user(self.reviewer).action_approve_manual_gateway_order(
            'Second approval, same order.')
        binding.invalidate_recordset()
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'order_import_sync')]),
            after_first,
            'a repeated approval must not enqueue a second refresh job',
        )
        self.assertEqual(binding.manual_gateway_approved_by_uid, actor)
        self.assertEqual(binding.manual_gateway_approved_at, at)

    # ------------------------------------------------------------------
    # The disclosure-only boundaries U2 deliberately keeps
    # ------------------------------------------------------------------

    def test_cod_surface_offers_no_separate_write_control(self):
        """COD is a ledger to read, not a form to post to.

        The U2 packet named "collection-event entry, discrepancy review" as
        deliverables and what shipped is display-only. That is a real scope
        gap, recorded as such -- but it must not be mistaken for a missing
        button on a surface that has one. This pins the shipped boundary so
        the copy deck describes what exists.
        """
        cod_list = self.env.ref(
            'shopify_connector_sale.'
            'view_shopify_connector_order_binding_cod_list'
        )
        self.assertNotIn(
            '<button', cod_list.arch,
            'the COD list must offer no write control',
        )
        cod_action = self.env.ref(COD_ACTION)
        workspace = self.env.ref(WORKSPACE_ACTION)
        self.assertEqual(
            cod_action.res_model, workspace.res_model,
            'COD reuses the order binding model and its S17 form, so its only '
            'action control is Approve Payment',
        )

    def test_customer_matching_offers_no_resolution_control(self):
        """Customer matching is read-only by design, and stays that way.

        `action_override_binding` exists on the binding mixin and is NOT wired
        to any U2 view: offering a re-bind one click from a list is exactly
        the affordance the matching surfaces refuse. Pinned so a later session
        cannot add the button without deciding to.
        """
        for xmlid in (
            'view_shopify_connector_customer_binding_list',
            'view_shopify_connector_customer_binding_form',
        ):
            view = self.env.ref('shopify_connector_sale.%s' % xmlid)
            self.assertNotIn(
                'action_override_binding', view.arch,
                '%s must not offer a binding-override control' % xmlid,
            )
            self.assertNotIn('<button', view.arch, '%s must have no button' % xmlid)
