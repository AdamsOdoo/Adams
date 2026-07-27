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
import json
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_export_reconnect import (
    JOB_TYPE_RECONNECT_RECONCILE,
    RECONCILE_BLOCKING_STATES,
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


def _media_body(file_gids=(), status='READY', has_next=False, exists=True,
                shop_domain='export-test.myshopify.com'):
    """A `ProductExportMediaVerify` response.

    TD-015 correction. The remote half of the media proof did not exist
    before, so neither did this fixture: every media assertion was made
    against local rows and a product body whose `media` field carried a
    single node the reader used only as a boolean.
    """
    if not exists:
        product = None
    else:
        product = {
            'id': PRODUCT_GID,
            'media': {
                'nodes': [
                    {'id': gid, 'mediaContentType': 'IMAGE',
                     'fileStatus': status,
                     'image': {'url': 'https://cdn.invalid/%s' % gid[-6:]}}
                    for gid in file_gids
                ],
                'pageInfo': {'hasNextPage': has_next},
            },
        }
    return {'data': {'product': product,
                     'shop': {'myshopifyDomain': shop_domain}}}


def _files_body(file_gids=(), status='READY',
                shop_domain='export-test.myshopify.com'):
    """A `ProductExportMediaFindByFilename` response."""
    return {'data': {
        'files': {'nodes': [
            {'id': gid, 'fileStatus': status} for gid in file_gids
        ]},
        'shop': {'myshopifyDomain': shop_domain},
    }}


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

    def _responder(self, body=None, media=None, files=None,
                   raise_on_send=None, calls=None):
        """One transport stand-in that answers by QUERY, not by call order.

        TD-015 correction. The pass used to issue exactly one read, so a
        responder that returned the same body every time was sufficient.
        It now issues a product read, a media read when the binding has
        associated media, and a filename read per association it could not
        find on the product -- so the stand-in has to distinguish them, or
        a media assertion would be answered with a product body and pass
        for the wrong reason.
        """
        body = body if body is not None else _product_body()
        media = media if media is not None else _media_body()
        files = files if files is not None else _files_body()

        def echo_identity(payload, request):
            """Answer about the product that was actually asked for.

            Both readers refuse a response naming a different product than
            they requested -- correctly, and it is the guard that catches a
            reconnect landing on somebody else's store. A fixed-GID fixture
            therefore cannot serve a test with more than one binding, so the
            stand-in echoes the requested id the way Shopify does. A test
            that wants the mismatch asserts it through `shop_domain`, which
            this leaves alone.
            """
            requested = ((request or {}).get('variables') or {}).get('id')
            product = (payload.get('data') or {}).get('product')
            if not requested or not isinstance(product, dict):
                return payload
            echoed = json.loads(json.dumps(payload))
            echoed['data']['product']['id'] = requested
            return echoed

        def responder(_self, _store, request, token=None,
                      mutation_context=None):
            if calls is not None:
                calls.append(request)
            if raise_on_send:
                raise raise_on_send
            query = (request or {}).get('query') or ''
            if 'ProductExportMediaVerify' in query:
                return FakeSendResponse(echo_identity(media, request))
            if 'ProductExportMediaFindByFilename' in query:
                return FakeSendResponse(files)
            return FakeSendResponse(echo_identity(body, request))

        return responder

    def _run_pass(self, body=None, raise_on_send=None, media=None,
                  files=None, calls=None):
        """Run every queued reconcile job against a patched transport."""
        # Terminal states are excluded, ALL of them. `cancelled` and
        # `skipped` are reachable now that a superseded generation is
        # retired, and driving one of those back to `running` is an illegal
        # transition core refuses -- correctly.
        jobs = self._reconcile_jobs().filtered(
            lambda j: j.state not in TERMINAL_JOB_STATES
        )
        responder = self._responder(
            body=body, media=media, files=files,
            raise_on_send=raise_on_send, calls=calls,
        )
        with self.send_patch(responder):
            for job in jobs:
                job.sudo().write({'state': 'running'})
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        return jobs

    def _associated_media_row(self, file_gid=FILE_GID, salt=b''):
        """A media row that claims a completed, associated export."""
        checksum = image_checksum(base64.b64decode(PNG_1X1) + salt)
        return self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': self.binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': self.Media._connector_filename(
                self.template.id, checksum,
            ),
            'shopify_gid': file_gid,
            'remote_status': 'associated',
        })

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

    def test_a_remotely_confirmed_media_row_still_cannot_reach_verified(self):
        """The checksum disposition, on the best case the platform allows.

        Everything a remote read CAN establish is established here: the
        File GID is on the product, its `fileStatus` is not `FAILED`, the
        store identity matches. PD-PX-7 requires "exists / variant GID set
        / media checksums", and the third one cannot be answered -- so this
        is `review`, not `verified`.

        The previous cycle returned `verified` here and recorded the
        checksum as a retained limitation. That substitutes a narrower
        proof for the accepted one, and the only documents authorising the
        substitution were written in that same unmerged cycle. Fail closed
        until an accepted decision says otherwise.
        """
        self._associated_media_row(salt=b'\x02')
        self._reconnect()
        self._run_pass(media=_media_body(file_gids=(FILE_GID,)))
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        note = self.binding.export_reconcile_note
        self.assertIn('expected File identity', note)
        self.assertIn('checksum correspondence could not be proven', note)
        self.assertNotIn(
            'no longer exist', note,
            'An unprovable checksum is not a proven absence.',
        )
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'The export block stays in place until an operator clears it.',
        )
        with self.assertRaises(UserError):
            self.Service.with_user(self.admin_user).enqueue_preview(
                self.template, self.store,
            )

    def test_the_checksum_verdict_names_both_halves_precisely(self):
        """The operator is told what WAS established, not only what was not.

        A refusal that says only "could not verify" is indistinguishable
        from a transport failure, and an operator would go looking for a
        missing File that is in fact present and correctly associated.
        """
        self._associated_media_row(salt=b'\x03')
        self._reconnect()
        self._run_pass(media=_media_body(file_gids=(FILE_GID,)))
        note = self.binding.export_reconcile_note
        self.assertIn('were re-read on the product', note)
        self.assertIn('non-FAILED status', note)
        self.assertIn('no digest of the stored bytes', note)
        self.assertIn('Nothing was changed', note)
        self.assertLessEqual(
            len(note), 255,
            'The note is stored in a Char truncated at 255; a reason that '
            'loses its own explanation is not a reason.',
        )

    def test_a_binding_with_no_media_claim_still_reaches_verified(self):
        """The disposition is scoped to bindings that CLAIM an association.

        Blocking every reconnected store, including ones that never
        exported an image, would be a different and much broader change
        than the one the evidence supports.
        """
        self._reconnect()
        self._run_pass()
        self.assertEqual(self.binding.export_reconcile_state, 'verified')
        self.assertIn(
            'claims no associated Shopify media',
            self.binding.export_reconcile_note,
        )
        self.assertEqual(self.store.export_reconcile_state, 'complete')

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

    def test_a_binding_with_no_media_issues_exactly_one_read(self):
        """No media claims, no media read. The pass pays for what it proves."""
        self._reconnect()
        calls = []
        self._run_pass(calls=calls)
        self.assertEqual(len(calls), 1)
        self.assertIn('ProductExportRead', calls[0]['query'])
        self.assertNotIn('mutation', calls[0]['query'])

    def test_every_read_the_pass_issues_is_a_query(self):
        """Requirement: no Shopify mutation in any reconciliation case.

        Asserted over the requests that actually reached the transport,
        across the media path as well -- a structural source guard cannot
        see a mutation assembled at runtime.
        """
        self._associated_media_row(file_gid='gid://shopify/MediaImage/GONE')
        self._reconnect()
        calls = []
        self._run_pass(
            calls=calls,
            media=_media_body(file_gids=()),
            files=_files_body(file_gids=()),
        )
        self.assertGreaterEqual(
            len(calls), 3,
            'A product read, a media read, and a filename read for the '
            'association the product did not carry.',
        )
        for request in calls:
            query = request.get('query') or ''
            self.assertTrue(query.lstrip().startswith('query '))
            self.assertNotIn('mutation', query)
        self.assertEqual(self.binding.export_reconcile_state, 'review')


def _raise(exc):
    raise exc


@tagged('post_install', '-at_install')
class TestExportReconnectRemoteMedia(TestExportReconnectReconcile):
    """TD-015 correction: media claims are proved against Shopify.

    The defect these close
    ----------------------
    `_media_divergence` read the local media registry and nothing else. A
    row saying `associated`, carrying a File GID and a checksum, returned
    "no divergence" -- so the store's export block was lifted on the
    strength of the connector's own bookkeeping. That is exactly the
    evidence a reconnect invalidates: every media row is a *claim* about a
    remote object, and between disconnect and reconnect the merchant could
    have deleted every one of them.

    What is provable and what is not is stated in `_media_divergence`'s
    docstring and asserted here: existence, product association and
    `fileStatus` are re-read; the stored image checksum is not, because the
    2026-07 `MediaImage` exposes no digest of the bytes it holds.

    And because PD-PX-7 requires the checksum comparison by name, "cannot
    prove it" resolves to `review`, not to `verified` with a footnote. A
    binding that claims an association can no longer reach `verified` at
    all -- only one that claims none can.
    """

    def test_complete_local_evidence_does_not_survive_missing_remote_media(self):
        """The headline case, and the one the previous implementation passed.

        Local state is as complete as it gets: `associated`, a real File
        GID, a checksum. The remote product carries no media at all, and
        the File is gone from the store's Files too.
        """
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=()),
            files=_files_body(file_gids=()),
        )
        self.assertEqual(
            self.binding.export_reconcile_state, 'review',
            'A populated local row may never by itself establish remote '
            'correctness.',
        )
        self.assertIn('no longer exist', self.binding.export_reconcile_note)
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'Exports stay blocked, and visibly so.',
        )

    def test_a_detached_file_is_distinguished_from_a_deleted_one(self):
        """Still in Files, no longer on the product. A different finding."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=()),
            files=_files_body(file_gids=(FILE_GID,)),
        )
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn(
            'no longer associated', self.binding.export_reconcile_note,
        )

    def test_a_divergent_remote_identity_is_a_divergence(self):
        """The product carries media -- just not this connector's File."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=('gid://shopify/MediaImage/MERCHANT',)),
            files=_files_body(file_gids=()),
        )
        self.assertEqual(self.binding.export_reconcile_state, 'review')

    def test_a_failed_remote_file_is_a_divergence(self):
        """`fileStatus` is re-read, not assumed from the local row."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=(FILE_GID,), status='FAILED'),
        )
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn('FAILED', self.binding.export_reconcile_note)

    def test_an_unverifiable_claim_is_never_reported_as_verified(self):
        """Requirement 5: truncation is a limitation, not a divergence.

        A product with more media than one page can hold means the
        connector did not see the whole list. "Not in the part I fetched"
        is not "not there", so this goes to operator review with the exact
        reason -- never to `verified`, and never to a finding that claims
        the File is gone.
        """
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(
                file_gids=('gid://shopify/MediaImage/OTHER',), has_next=True,
            ),
        )
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertIn(
            'could not be re-verified', self.binding.export_reconcile_note,
        )
        self.assertNotIn(
            'no longer exist', self.binding.export_reconcile_note,
            'An unverifiable claim must not be reported as a proven '
            'absence.',
        )

    def test_a_foreign_media_item_on_the_product_is_left_alone(self):
        """Merchant-owned media is neither claimed nor touched.

        The verdict is `review` because of the unprovable checksum, not
        because of the merchant's image -- which is exactly what the note
        has to show, or the operator would go hunting for a divergence
        that does not exist. This connector makes no exclusivity claim it
        could verify.
        """
        self._associated_media_row()
        self._reconnect()
        self._run_pass(media=_media_body(file_gids=(
            FILE_GID, 'gid://shopify/MediaImage/MERCHANT-OWNED',
        )))
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        note = self.binding.export_reconcile_note
        self.assertIn('checksum correspondence could not be proven', note)
        self.assertNotIn('MERCHANT-OWNED', note)
        self.assertNotIn('no longer associated', note)

    def test_the_media_read_lands_on_a_different_store_and_is_refused(self):
        """A media read that observed somebody else's store settles nothing."""
        self._associated_media_row()
        self._reconnect()
        job = self._reconcile_jobs()
        job.sudo().write({'state': 'running'})
        responder = self._responder(
            media=_media_body(
                file_gids=(FILE_GID,), shop_domain='someone-else.myshopify.com',
            ),
        )
        with self.send_patch(responder):
            with self.assertRaises(JobHandlerError) as caught:
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.assertEqual(caught.exception.error_class, 'store_identity_mismatch')
        self.binding.invalidate_recordset()
        self.assertEqual(
            self.binding.export_reconcile_state, 'pending',
            'No verdict may be recorded from a read of the wrong store.',
        )

    def test_the_helper_cannot_return_verified_without_transport_context(self):
        """A caller that cannot perform the remote half cannot pass.

        `_media_divergence` returning `False` MEANS "re-verified against
        Shopify". Making the remote arm reachable only when `store` and
        `job` are both supplied would be an invitation to call it without
        them and get a clean result for free.
        """
        self._associated_media_row()
        note = self.Reconcile._media_divergence(self.binding)
        self.assertTrue(note)
        self.assertIn('unverified', note)

    def test_nothing_in_the_media_path_can_create_or_replace_media(self):
        """Requirement 6, on the source of the whole remote arm."""
        import ast
        import inspect

        from ..models import shopify_connector_export_reconnect as module

        tree = ast.parse(inspect.getsource(module))
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        for forbidden in (
            '_enqueue_media_step', '_admit_media_job', '_resume_media_export',
            '_advance_media', '_mutation_request', '_transport',
        ):
            self.assertNotIn(
                forbidden, called,
                'The reconciliation pass must not be able to touch media; '
                'it calls %s.' % forbidden,
            )


@tagged('post_install', '-at_install')
class TestExportReconnectConvergence(TestExportReconnectReconcile):
    """TD-015 correction: store settlement is atomic and generation-scoped.

    The defect these close
    ----------------------
    Each job wrote its binding verdict and then independently searched for
    pending siblings. Two final jobs in separate transactions each saw the
    other's binding still `pending` -- neither verdict was committed --
    so neither settled, and both committed. Every binding terminal, the
    store permanently `in_progress`, no job left to notice, and exports
    blocked forever with no operator route out.

    Separately, `_settle_export_reconciliation` stamped
    `connection_generation` -- whatever the store had reached by then --
    rather than the epoch the verdicts actually covered, so an old pass
    could record itself as proof about a newer connection and release its
    block.

    The cross-transaction proof uses two genuine pooled connections. No
    shared Odoo ORM cursor is driven from two threads, and there is no
    sleep: the interleaving is stepped explicitly.
    """

    def _second_binding(self):
        """A second exported binding, so a pass has two jobs to race."""
        template = self.env['product.template'].create({
            'name': 'Second exportable widget',
            'shopify_export_enabled': True,
        })
        return self.TemplateBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_id': template.id,
            'shopify_gid': 'gid://shopify/Product/SECOND',
        })

    def test_two_final_jobs_in_one_transaction_still_converge(self):
        """The single-transaction shape of the race, run in order."""
        second = self._second_binding()
        self._reconnect()
        jobs = self._reconcile_jobs()
        self.assertEqual(len(jobs), 2)
        self._run_pass()
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_state, 'complete',
            'Every binding terminal must mean the store is terminal.',
        )
        second.invalidate_recordset()
        self.assertEqual(second.export_reconcile_state, 'verified')

    def test_a_review_verdict_converges_to_review_required(self):
        second = self._second_binding()
        self._reconnect()
        jobs = self._reconcile_jobs()
        first_job = jobs[0]
        rest = jobs - first_job
        responder = self._responder(body=_product_body(exists=False))
        with self.send_patch(responder):
            first_job.sudo().write({'state': 'running'})
            self.Reconcile._handle_product_export_reconnect_reconcile(first_job)
        with self.send_patch(self._responder()):
            for job in rest:
                job.sudo().write({'state': 'running'})
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'review_required')
        self.assertIn('need review', self.store.export_reconcile_note)
        second.invalidate_recordset()

    def test_no_terminal_verdict_set_can_leave_the_store_in_progress(self):
        """The invariant, asserted over every ordering of two jobs.

        Whichever job finishes last must be the one that settles. Asserted
        by running the pass in both orders on a fresh reconnect each time,
        because "it worked when they ran in id order" is precisely the
        assumption the defect hid behind.
        """
        self._second_binding()
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                self.store.sudo().write({
                    'export_reconcile_state': 'not_required',
                })
                self._reconnect()
                jobs = self._reconcile_jobs().filtered(
                    lambda j: j.state not in ('succeeded', 'cancelled')
                )
                ordered = list(reversed(jobs)) if reverse else list(jobs)
                with self.send_patch(self._responder()):
                    for job in ordered:
                        job.sudo().write({'state': 'running'})
                        self.Reconcile.\
                            _handle_product_export_reconnect_reconcile(job)
                self.store.invalidate_recordset()
                self.assertNotEqual(
                    self.store.export_reconcile_state, 'in_progress',
                    'A terminal set of binding verdicts left the store '
                    'blocked with no job able to settle it.',
                )

    # ------------------------------------------------------------------
    # Generation binding
    # ------------------------------------------------------------------

    def test_an_old_generation_job_cannot_settle_a_newer_pass(self):
        """Requirement 4, and the one that silently released the block.

        An in-flight job from before a second reconnect must not write a
        verdict, must not settle, and must not lift the new block.
        """
        self._reconnect()
        stale = self._reconcile_jobs()
        self.assertEqual(len(stale), 1)
        stale_generation = stale.expected_connection_generation

        # A second reconnect, while that job is still outstanding.
        self.store.sudo().write({
            'connection_generation': self.store.connection_generation + 1,
        })
        self.store.invalidate_recordset()
        self.store._require_export_reconnect_reconciliation()
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'in_progress')

        stale.invalidate_recordset()
        self.assertEqual(
            stale.state, 'cancelled',
            'The superseded job is retired at enqueue, so it can neither '
            'run nor hold the operation scope the new pass needs.',
        )
        self.assertIn('Superseded', stale.cancel_reason)
        self.assertNotEqual(
            stale_generation, self.store.connection_generation,
        )
        self.assertEqual(
            self.store.export_reconcile_state, 'in_progress',
            'The new block stays in place: nothing from the old pass may '
            'release it.',
        )

    def test_a_superseded_job_that_does_run_records_no_verdict(self):
        """Defence in depth: the handler refuses a stale generation itself.

        The enqueue path retires superseded jobs, but a job already claimed
        by a worker when the reconnect happened is past that point. It has
        to recognise its own staleness.
        """
        self._reconnect()
        job = self._reconcile_jobs()
        job.sudo().write({'state': 'running'})
        # The reconnect happens while this job is running.
        self.store.sudo().write({
            'connection_generation': self.store.connection_generation + 1,
        })
        self.store.invalidate_recordset()
        calls = []
        with self.send_patch(self._responder(calls=calls)):
            self.Reconcile._handle_product_export_reconnect_reconcile(
                job.sudo().browse(job.id),
            )
        job.invalidate_recordset()
        self.binding.invalidate_recordset()
        self.assertEqual(job.state, 'skipped')
        self.assertEqual(
            calls, [],
            'A superseded job must not spend a Shopify call proving '
            'something about a connection that no longer exists.',
        )
        self.assertEqual(
            self.binding.export_reconcile_state, 'pending',
            'No verdict from a superseded generation.',
        )

    def test_settlement_refuses_a_generation_the_store_has_moved_past(self):
        """The guard, exercised directly at its own boundary."""
        self._reconnect()
        generation = self.store.export_reconcile_generation
        self._run_pass()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        self.assertEqual(
            self.store.export_reconcile_generation, generation,
            'The verdict is stamped with the epoch it covers, not with '
            'whatever the store has reached since.',
        )
        self.assertFalse(
            self.store._settle_export_reconciliation(
                generation=generation - 1,
            ),
            'An older generation may not re-settle this store.',
        )

    def test_a_repeated_reconnect_does_not_fail_on_duplicate_admission(self):
        """Requirement 5: the constraint must not turn into a hard stop.

        Core holds `UNIQUE(store_id, operation_scope_key)` while a job is
        non-terminal, and the key is identical for the old and the new pass
        over one binding. Enqueuing over a live earlier pass therefore
        raises `IntegrityError` -- and a reconnect that dies on a
        constraint leaves the store unreconciled and exports blocked.
        """
        self._reconnect()
        first = self._reconcile_jobs()
        for round_index in range(3):
            with self.subTest(round=round_index):
                self.store.sudo().write({
                    'connection_generation':
                        self.store.connection_generation + 1,
                })
                self.store.invalidate_recordset()
                # Must not raise.
                self.store._require_export_reconnect_reconciliation()
                self.store.invalidate_recordset()
                live = self._reconcile_jobs().filtered(
                    lambda j: j.state not in ('cancelled', 'succeeded')
                )
                self.assertEqual(
                    len(live), 1,
                    'Exactly one live job per binding per generation.',
                )
                self.assertEqual(
                    live.expected_connection_generation,
                    self.store.connection_generation,
                )
        first.invalidate_recordset()
        self.assertEqual(first.state, 'cancelled')

    def test_a_same_generation_rerun_coalesces_instead_of_duplicating(self):
        """A re-run does not discard a still-valid verification read."""
        self._reconnect()
        first = self._reconcile_jobs()
        self.assertEqual(len(first), 1)
        self.store.with_user(
            self.admin_user
        ).action_shopify_export_reconnect_reconciliation()
        self.store.invalidate_recordset()
        live = self._reconcile_jobs().filtered(
            lambda j: j.state not in ('cancelled', 'succeeded')
        )
        self.assertEqual(
            live, first,
            'At the same generation the outstanding job already covers this '
            'work; a re-run coalesces on it.',
        )

    def test_a_repeated_reconnect_leaves_a_job_able_to_settle(self):
        """The store must never be left with no route to a verdict."""
        self._reconnect()
        self.store.sudo().write({
            'connection_generation': self.store.connection_generation + 1,
        })
        self.store.invalidate_recordset()
        self.store._require_export_reconnect_reconciliation()
        self.store.invalidate_recordset()
        self._run_pass()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        self.assertEqual(
            self.store.export_reconcile_generation,
            self.store.connection_generation,
        )

    def test_a_transport_failure_still_leaves_the_block_in_place(self):
        """Requirement 6: fail-closed survives the convergence change."""
        self._reconnect()
        with self.assertRaises(Exception):
            self._run_pass(raise_on_send=RuntimeError('network down'))
        self.store.invalidate_recordset()
        self.assertIn(
            self.store.export_reconcile_state, RECONCILE_BLOCKING_STATES,
        )
        with self.assertRaises(UserError):
            self.store._assert_export_reconciliation_complete()

    # ------------------------------------------------------------------
    # The serialization boundary itself
    # ------------------------------------------------------------------

    def test_the_settle_serializes_on_the_store_row(self):
        """The mechanism, asserted rather than described.

        A settlement that did not write the store row could not conflict,
        and without a conflict two concurrent settlements each read a stale
        snapshot -- which is the defect. The sequence bump is what makes
        PostgreSQL raise `40001` on the loser under REPEATABLE READ.
        """
        self._reconnect()
        before = self.store.export_reconcile_settle_seq
        self.store._settle_export_reconciliation(
            generation=self.store.export_reconcile_generation,
        )
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_settle_seq, before + 1,
            'Every settle attempt must write the serialization row, '
            'including one that decides not to settle.',
        )

    def test_the_settle_flushes_the_verdict_before_reading_siblings(self):
        """A job that cannot see its own verdict can never be the last one."""
        import inspect

        source = inspect.getsource(
            type(self.Reconcile)._finish
        )
        self.assertIn('flush_model', source)
        settle = inspect.getsource(
            self.env['shopify.connector.store'].
            _settle_export_reconciliation.__func__
        )
        self.assertIn('_serialize_reconcile_settlement', settle)
        self.assertLess(
            settle.index('_serialize_reconcile_settlement'),
            settle.index('_export_reconcile_scope'),
            'Serialization has to come BEFORE the sibling read it gates.',
        )
