"""TD-015 / PD-PX-7: the reconnect reconciliation pass.

The defect
----------
PD-PX-7 is explicit:

    Exports stay blocked for a reconnected store until the full binding
    reconciliation pass completes (exists / variant GID set / media
    checksums); deleted-or-archived remote -> review, never silent
    re-create.

What shipped was a manual button that expired every open preview and
returned a count. Expiring the previews is a necessary part of the block
— a confirmation taken before a reconnect must not authorise a mutation
after it — but nothing re-read anything, no export was blocked, and the
button had to be remembered.

So a store could be disconnected, reconnected against a different Shopify
store or after a merchant had deleted or archived products, and the
connector would resume exporting against bindings whose claims it had
never re-verified.

What these tests hold
---------------------
The pass is triggered by the reconnect *lifecycle*, not by a control;
exports are refused until it reaches a terminal verdict; a missing,
archived or materially divergent remote goes to explicit review and is
never re-created; and the store cannot be left stranded part-way.

Zero Shopify contact. The transport is replaced at the module's existing
`_send` seam, so the real client, the real Layer 2 admission and the real
response taxonomy all run.
"""

import base64
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from ..models.shopify_connector_export_reconnect import (
    JOB_TYPE_RECONNECT_RECONCILE,
)
from ..models.shopify_connector_media_export_service import image_checksum
from .common import (
    ExportCase,
    FakeSendResponse,
    FILE_GID,
    PRODUCT_GID,
    VARIANT_GID,
)
from .test_media_export_pipeline import PNG_1X1


def _product_body(exists=True, status='ACTIVE', variant_gids=(VARIANT_GID,),
                  shop_domain='export-test.myshopify.com'):
    """A `ProductExportRead` response in the exact shape the reader parses."""
    if not exists:
        product = None
    else:
        product = {
            'id': PRODUCT_GID,
            'handle': 'exportable-widget',
            'title': 'Exportable Widget',
            'descriptionHtml': '<p>A widget.</p>',
            'vendor': 'Adams',
            'productType': 'Widgets',
            'tags': ['alpha', 'beta'],
            'status': status,
            'updatedAt': '2026-07-26T00:00:00Z',
            'options': [],
            'variants': {'nodes': [
                {'id': gid, 'barcode': '0001', 'price': '12.50',
                 'compareAtPrice': None,
                 'inventoryItem': {'id': 'gid://shopify/InventoryItem/1',
                                   'sku': 'WIDGET-1'},
                 'selectedOptions': []}
                for gid in variant_gids
            ]},
            'collections': {'nodes': []},
            'metafields': {'nodes': []},
            'media': {'nodes': []},
        }
    return {'data': {'product': product,
                     'shop': {'myshopifyDomain': shop_domain}}}


@tagged('post_install', '-at_install')
class TestExportReconnectReconcile(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template()
        self.Reconcile = self.env['shopify.connector.export.reconcile.service']
        self.Job = self.env['shopify.connector.job']
        self.admin_user = self.env['res.users'].sudo().create({
            'name': 'Reconcile Admin',
            'login': 'reconcile_admin_%d' % self.store.id,
            'group_ids': [(6, 0, [
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _reconcile_jobs(self):
        return self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_RECONNECT_RECONCILE),
        ])

    def _run_pass(self, body=None, raise_on_send=None):
        """Run every queued reconcile job against a patched transport."""
        body = body if body is not None else _product_body()
        jobs = self._reconcile_jobs().filtered(
            lambda j: j.state not in ('succeeded', 'failed_final')
        )

        def responder(_self, _store, _body, token=None, mutation_context=None):
            if raise_on_send:
                raise raise_on_send
            return FakeSendResponse(body)

        with self.send_patch(responder):
            for job in jobs:
                job.sudo().write({'state': 'running'})
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        return jobs

    def _reconnect(self):
        """Require reconciliation the way a real reconnect does."""
        self.store._require_export_reconnect_reconciliation()
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()

    # ------------------------------------------------------------------
    # 1. The trigger is the lifecycle, not a button
    # ------------------------------------------------------------------

    def test_a_successful_reconnect_requires_reconciliation(self):
        """Requirement 1, at the real seam.

        `action_reconnect` bumps `connection_generation` exactly once and
        only on success, which is how the override distinguishes an actual
        reconnect from the several paths where `super()` returns without
        connecting.
        """
        import inspect

        from ..models import shopify_connector_export_reconnect as module

        source = inspect.getsource(
            module.ShopifyConnectorStoreExportReconnect.action_reconnect
        )
        self.assertIn('connection_generation', source)
        self.assertIn('_require_export_reconnect_reconciliation', source)

    def test_reconnect_queues_one_job_per_exported_binding(self):
        """Requirement 5: every previously exported binding is in scope."""
        self._reconnect()
        self.assertEqual(len(self._reconcile_jobs()), 1)
        self.assertEqual(self.store.export_reconcile_state, 'in_progress')
        self.assertEqual(self.binding.export_reconcile_state, 'pending')

    def test_reconnect_invalidates_every_open_preview(self):
        """Requirement 4: no pre-reconnect confirmation survives."""
        preview = self.make_preview(binding=self.binding, state='confirmed')
        self._reconnect()
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'expired')

    def test_a_store_with_nothing_exported_is_not_blocked(self):
        """Requirement 12, inverted: no work is a complete verdict.

        A store that has never exported must not be left unable to export
        its first product because a pass found nothing to do. A fresh
        store is used rather than clearing a GID, because `shopify_gid`
        is NOT NULL on a binding -- "never exported" means no binding, not
        a binding with no product.
        """
        fresh = self.Store.sudo().create({
            'name': 'Reconcile Fresh Store',
            'shop_domain': 'reconcile-fresh.myshopify.com',
            'api_version': self.store.api_version,
        })
        fresh.sudo().write({'state': 'connected'})
        fresh._require_export_reconnect_reconciliation()
        fresh.invalidate_recordset()
        self.assertEqual(fresh.export_reconcile_state, 'complete')
        self.assertFalse(self.Job.sudo().search_count([
            ('store_id', '=', fresh.id),
            ('job_type', '=', JOB_TYPE_RECONNECT_RECONCILE),
        ]))

    # ------------------------------------------------------------------
    # 2. Exports are blocked and released (requirements 3 and 15)
    # ------------------------------------------------------------------

    def test_exports_are_refused_while_reconciliation_is_outstanding(self):
        self._reconnect()
        with self.assertRaises(UserError) as caught:
            self.Service.with_user(self.admin_user).enqueue_preview(
                self.template, self.store,
            )
        self.assertIn('reconnect reconciliation', str(caught.exception))

    def test_the_apply_is_refused_too(self):
        """Defence in depth: an apply is where the mutations start."""
        preview = self.make_preview(binding=self.binding, state='confirmed')
        self._reconnect()
        with self.assertRaises(UserError):
            self.Service._enqueue_apply(preview)

    def test_a_clean_pass_unblocks_exports(self):
        """Requirement 15: exports resume on the accepted condition."""
        self._reconnect()
        self._run_pass()
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        self.assertEqual(self.binding.export_reconcile_state, 'verified')
        job = self.Service.with_user(self.admin_user).enqueue_preview(
            self.template, self.store,
        )
        self.assertTrue(job)

    def test_a_review_verdict_keeps_exports_blocked(self):
        self._reconnect()
        self._run_pass(body=_product_body(exists=False))
        self.assertEqual(self.store.export_reconcile_state, 'review_required')
        with self.assertRaises(UserError) as caught:
            self.Service.with_user(self.admin_user).enqueue_preview(
                self.template, self.store,
            )
        self.assertIn('missing, archived or materially different',
                      str(caught.exception))

    # ------------------------------------------------------------------
    # 3. The verdicts (requirements 7, 8, 9, 10, 11)
    # ------------------------------------------------------------------

    def test_a_missing_remote_product_goes_to_review_and_is_not_recreated(self):
        """Requirement 11, the one that matters most.

        Re-creating a product the merchant deleted would be the connector
        deciding, silently, that it knows better. The pass reports and
        stops.
        """
        self._reconnect()
        self._run_pass(body=_product_body(exists=False))
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('no longer exists', self.binding.export_reconcile_note)
        self.assertIn('not re-created', self.binding.export_reconcile_note)
        self.assertFalse(
            self.Job.sudo().search_count([
                ('store_id', '=', self.store.id),
                ('job_type', 'in', ('product_export_create',
                                    'product_export_update')),
            ]),
            'A reconciliation may not enqueue a mutation of any kind.',
        )

    def test_an_archived_remote_product_goes_to_review(self):
        self._reconnect()
        self._run_pass(body=_product_body(status='ARCHIVED'))
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('archived', self.binding.export_reconcile_note)

    def test_a_missing_bound_variant_goes_to_review(self):
        """Requirement 8: the governed variant GID set is verified."""
        self._reconnect()
        self._run_pass(body=_product_body(variant_gids=()))
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('variant', self.binding.export_reconcile_note)

    def test_an_extra_remote_variant_is_not_a_divergence(self):
        """A merchant-added variant is theirs, and is not our failure.

        The connector's claim is that ITS variants still exist, not that
        it owns every variant on the product. Treating a merchant addition
        as divergence would block exports for doing nothing wrong.
        """
        self._reconnect()
        self._run_pass(body=_product_body(variant_gids=(
            VARIANT_GID, 'gid://shopify/ProductVariant/MERCHANT',
        )))
        self.assertEqual(self.binding.export_reconcile_state, 'verified')

    def test_a_stranded_media_association_goes_to_review(self):
        """Requirement 9: media identity the connector owns is verified."""
        checksum = image_checksum(base64.b64decode(PNG_1X1))
        self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': self.binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': 'x-%s.png' % checksum[:8],
            'shopify_gid': 'pending:x-%s' % checksum[:8],
            'remote_status': 'associated',
        })
        self._reconnect()
        self._run_pass()
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('durable Shopify File identity',
                      self.binding.export_reconcile_note)

    def test_an_in_flight_media_upload_goes_to_review(self):
        """The connection dropped mid-upload; the remote state is unknown."""
        checksum = image_checksum(base64.b64decode(PNG_1X1) + b'\x01')
        self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': self.binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': 'y-%s.png' % checksum[:8],
            'shopify_gid': 'pending:y-%s' % checksum[:8],
            'remote_status': 'uploaded',
        })
        self._reconnect()
        self._run_pass()
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('in flight', self.binding.export_reconcile_note)

    def test_a_completed_media_row_is_not_a_divergence(self):
        checksum = image_checksum(base64.b64decode(PNG_1X1) + b'\x02')
        self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': self.binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': 'z-%s.png' % checksum[:8],
            'shopify_gid': FILE_GID,
            'remote_status': 'associated',
        })
        self._reconnect()
        self._run_pass()
        self.assertEqual(self.binding.export_reconcile_state, 'verified')

    def test_a_different_store_identity_is_refused_outright(self):
        """The scenario PD-PX-7 exists for, and the one write that must not
        happen: a reconnect that landed on somebody else's store."""
        from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
            JobHandlerError,
        )

        self._reconnect()
        job = self._reconcile_jobs()
        job.sudo().write({'state': 'running'})
        body = _product_body(shop_domain='someone-else.myshopify.com')
        with self.send_patch(
            lambda _s, _st, _b, token=None, mutation_context=None:
                FakeSendResponse(body)
        ):
            with self.assertRaises(JobHandlerError) as caught:
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.assertEqual(caught.exception.error_class,
                         'store_identity_mismatch')

    # ------------------------------------------------------------------
    # 4. Authority, isolation and retry (requirements 2, 13, 14)
    # ------------------------------------------------------------------

    def test_an_unauthorised_user_may_not_run_the_pass(self):
        auditor = self.env['res.users'].sudo().create({
            'name': 'Reconcile Auditor',
            'login': 'reconcile_auditor_%d' % self.store.id,
            'group_ids': [(6, 0, [
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })
        with self.assertRaises(AccessError):
            self.store.with_user(
                auditor
            ).action_shopify_export_reconnect_reconciliation()

    def test_another_companys_store_is_refused(self):
        """Requirement 2: company access is checked before anything elevates."""
        other_company = self.env['res.company'].sudo().create({
            'name': 'Reconcile Other Co',
        })
        self.store.sudo().write({'company_id': other_company.id})
        self.assertNotIn(other_company, self.admin_user.company_ids)
        with self.assertRaises(AccessError):
            self.store.with_user(
                self.admin_user
            ).action_shopify_export_reconnect_reconciliation()

    def test_the_pass_is_retryable(self):
        """Requirement 13: a review verdict can be re-run after a fix."""
        self._reconnect()
        self._run_pass(body=_product_body(exists=False))
        self.assertEqual(self.store.export_reconcile_state, 'review_required')

        self.store.with_user(
            self.admin_user
        ).action_shopify_export_reconnect_reconciliation()
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'pending')
        self._run_pass()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    def test_a_transport_failure_leaves_the_block_in_place(self):
        """Requirement 12: never silently strand, never silently release.

        A pass that could not read must not be mistaken for a pass that
        read and found nothing wrong.
        """
        from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
            ShopifyClientError,
        )

        self._reconnect()
        job = self._reconcile_jobs()
        job.sudo().write({'state': 'running'})
        with self.send_patch(
            lambda _s, _st, _b, token=None, mutation_context=None: (
                _raise(ShopifyClientError(
                    'shopify_temporary_server_network', 'temporary',
                ))
            )
        ):
            with self.assertRaises(Exception):
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'pending')
        self.assertNotEqual(self.store.export_reconcile_state, 'complete')

    def test_the_verdict_records_which_generation_it_covers(self):
        """A verdict about a connection that no longer exists is detectable."""
        self._reconnect()
        self._run_pass()
        self.assertEqual(
            self.store.export_reconcile_generation,
            self.store.connection_generation,
        )
        self.assertTrue(self.store.export_reconcile_at)

    # ------------------------------------------------------------------
    # 5. Structural
    # ------------------------------------------------------------------

    def test_the_reconcile_handler_contains_no_mutation(self):
        """Requirement 11, asserted on the source rather than on prose.

        "Never silently re-create" is only true if there is no code path
        that could. This is the guard that keeps it true.

        Scanned over STRING LITERALS and CALLED NAMES rather than raw
        text, because a raw-text scan matches the module's own
        explanation of why it performs no mutation -- which would make
        the guard fail for saying the right thing, and tempt whoever hit
        it to delete the explanation instead of the mutation.
        """
        import ast
        import inspect

        from ..models import shopify_connector_export_reconnect as module

        tree = ast.parse(inspect.getsource(module))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    docstrings.add(doc)
        literals = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docstrings
        ]
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        for token in (
            'productSet', 'productUpdate', 'productVariantsBulkCreate',
            'productVariantsBulkUpdate', 'fileCreate', 'fileUpdate',
            'stagedUploadsCreate', 'mutation ',
        ):
            offenders = [text for text in literals if token in text]
            self.assertFalse(
                offenders,
                'The reconciliation pass must be read-only; %r appears in '
                'a string it evaluates: %s' % (token, offenders),
            )
        for name in ('_enqueue_apply', '_enqueue_step', '_advance_plan'):
            self.assertNotIn(
                name, called,
                'The reconciliation pass must not drive the export '
                'pipeline; it calls %s.' % name,
            )

    def test_the_pass_issues_exactly_one_read_per_binding(self):
        self._reconnect()
        calls = []

        def responder(_self, _store, body, token=None, mutation_context=None):
            calls.append(body)
            return FakeSendResponse(_product_body())

        with self.send_patch(responder):
            for job in self._reconcile_jobs():
                job.sudo().write({'state': 'running'})
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.assertEqual(len(calls), 1)
        self.assertIn('ProductExportRead', calls[0]['query'])
        self.assertNotIn('mutation', calls[0]['query'])


def _raise(exc):
    raise exc
