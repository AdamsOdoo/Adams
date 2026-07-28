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
import contextlib
import hashlib
import inspect
import json
import logging
import uuid
from unittest.mock import patch

import psycopg2
import psycopg2.errorcodes

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessError, UserError
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_export_reconnect import (
    JOB_TYPE_RECONNECT_RECONCILE,
    RECONCILE_BLOCKING_STATES,
    RECONCILE_REVALIDATION_BATCH_SIZE,
)
from ..models.shopify_connector_media_export_service import image_checksum
from .common import (
    DUMMY_TOKEN,
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

    def test_truncation_is_never_masked_by_every_claimed_file_being_present(
        self,
    ):
        """Correction C (independent review, Defect #4).

        The predecessor checked "every claimed File was found" BEFORE
        checking `hasNextPage`, on the reasoning that `absent` is empty
        exactly when every claimed File was seen. That reasoning is a
        non-sequitur: every claimed File landing on the ONE page this pass
        read does not prove the whole media list was read -- pages this
        pass never saw could still hold a divergence. A product with more
        media than one page holds, whose connector-owned images happen to
        land in the first page, must still go to `media_read_truncated`,
        never to the acknowledgeable `checksum_unverifiable` reason.
        """
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=(FILE_GID,), has_next=True),
        )
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertEqual(
            self.binding.export_reconcile_reason, 'media_read_truncated',
            'Every claimed File appearing on the page that WAS read must '
            'not be reported as a complete, checksum-unverifiable read.',
        )
        self.assertIn(
            'could not be re-verified', self.binding.export_reconcile_note,
        )
        self.assertEqual(self.store.export_reconcile_state, 'review_required')

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
        reason, note = self.Reconcile._media_divergence(self.binding)
        self.assertTrue(note)
        self.assertIn('unverified', note)
        self.assertEqual(
            reason, 'media_not_reread',
            'The machine-readable reason must say the remote half did not '
            'run, so nothing downstream can treat it as acknowledgeable.',
        )

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

    What this class does and does NOT prove
    ---------------------------------------
    Every test below runs in the single shared `TransactionCase` cursor.
    They cover ordering, the terminal-set invariant, generation binding and
    the mechanism's own shape -- and they are **not** a cross-transaction
    proof, because one transaction cannot produce a serialization conflict
    with itself. An earlier version of this docstring claimed they used
    "two genuine pooled connections"; they never did.

    The genuine cross-transaction proof is
    `TestExportReconnectSettlementRace` at the foot of this file, on two
    independent `db_connect` connections through the production dispatcher.
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


@tagged('post_install', '-at_install')
class TestExportReconnectChecksumAcknowledgement(TestExportReconnectReconcile):
    """TD-015 operator resolution: the one review that can be resolved.

    The defect this closes
    ----------------------
    The preceding cycle routed every media-bearing binding to `review` --
    correctly, because Shopify exposes no digest of a stored File's bytes and
    PD-PX-7 requires media checksums to be verified. It then recorded, in the
    code and in the PR, that "an operator must clear it before exports
    resume".

    No route existed that could clear it. The only public action re-RAN the
    pass, which re-read the same product, re-derived the same unprovable
    checksum and landed in the same review. `export_reconcile_state` was
    displayed on no screen anywhere in the product. So a reconnected store
    that had ever exported product media was blocked from exporting
    permanently, by construction, and the operator had nothing to click.

    A fail-closed design with no door is not fail-closed; it is an outage
    with a good explanation.

    What these tests hold
    ---------------------
    Exactly one review reason is resolvable, and it is resolvable only by a
    Connector Administrator, only for the company that owns the store, only
    against the exact evidence the pass recorded, only with an explicit
    consequence-stating confirmation, and only without touching Shopify at
    all. Every other finding -- missing, archived, detached, failed, foreign,
    truncated, in-flight, variant-divergent -- stays blocked, and the tests
    below drive each one through the real handler rather than asserting it
    from a constructed state.
    """

    def setUp(self):
        super().setUp()
        self.Wizard = self.env['shopify.connector.export.checksum.ack.wizard']
        self.connector_user = self.env['res.users'].sudo().create({
            'name': 'Reconcile Connector User',
            'login': 'reconcile_user_%d' % self.store.id,
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_user'
                ).id,
            ])],
        })
        self.admin_user.sudo().write({
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(4, self.env.ref('base.group_user').id)],
        })
        self.other_company = self.env['res.company'].sudo().create({
            'name': 'TD-015 other company',
        })
        # An ADMINISTRATOR of another company. The distinction matters: this
        # user holds every connector right and is refused purely on ownership,
        # which is the only way to observe the company axis rather than the
        # role axis.
        self.other_admin = self.env['res.users'].sudo().create({
            'name': 'Other Company Admin',
            'login': 'reconcile_other_admin_%d' % self.store.id,
            'company_id': self.other_company.id,
            'company_ids': [(6, 0, [self.other_company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _reach_checksum_review(self, file_gid=FILE_GID):
        """Drive the REAL pass to the one acknowledgeable outcome.

        Constructed state is deliberately not used here. The whole security
        claim is that this reason is reachable only after store identity,
        product identity, archive state, the variant set, File identity, File
        status and response completeness have all been established -- and the
        only way to assert that is to make the handler establish them.
        """
        self._associated_media_row(file_gid=file_gid)
        self._reconnect()
        self._run_pass(media=_media_body(file_gids=(file_gid,)))
        self.binding.invalidate_recordset()
        self.store.invalidate_recordset()
        return self.binding

    def _ack(self, user=None, confirmed=True, binding=None):
        binding = binding if binding is not None else self.binding
        record = binding.with_user(user) if user is not None else binding
        return record.action_shopify_export_acknowledge_checksum(
            confirmed=confirmed,
        )

    # ------------------------------------------------------------------
    # 1. The gap itself
    # ------------------------------------------------------------------

    def test_a_media_bearing_binding_reaches_the_acknowledgeable_reason(self):
        """The pass records a machine-readable reason, not only prose."""
        self._reach_checksum_review()
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertEqual(
            self.binding.export_reconcile_reason, 'checksum_unverifiable',
        )
        self.assertEqual(self.store.export_reconcile_state, 'review_required')
        with self.assertRaises(UserError):
            self.store._assert_export_reconciliation_complete()

    def test_re_running_the_pass_alone_can_never_clear_the_block(self):
        """The defect, stated as a test.

        Re-running was the ONLY public route that existed. It re-reads the
        same product and re-derives the same unprovable checksum, so it can
        never be the resolution -- which is exactly why a resolution route
        had to exist.
        """
        self._reach_checksum_review()
        for _attempt in range(3):
            self.store.with_user(self.admin_user).\
                action_shopify_export_reconnect_reconciliation()
            self._run_pass(media=_media_body(file_gids=(FILE_GID,)))
            self.store.invalidate_recordset()
            self.assertEqual(
                self.store.export_reconcile_state, 'review_required',
                'Re-running the pass cannot resolve an unprovable checksum.',
            )

    def test_eligibility_is_decided_from_the_reason_not_from_the_note(self):
        """Requirement 4: a copy edit must never be an authorization change."""
        self._reach_checksum_review()
        self.binding.sudo().write({
            'export_reconcile_note': 'Completely rewritten operator copy.',
        })
        self.binding.invalidate_recordset()
        self._ack(user=self.admin_user)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    # ------------------------------------------------------------------
    # 2. The route works, end to end, for the right person
    # ------------------------------------------------------------------

    def test_an_administrator_can_acknowledge_and_the_store_converges(self):
        """Requirement 11, through the production method."""
        self._reach_checksum_review()
        self.assertTrue(self._ack(user=self.admin_user))
        self.binding.invalidate_recordset()
        self.store.invalidate_recordset()
        self.assertTrue(self.binding.export_reconcile_ack_at)
        self.assertEqual(
            self.binding.export_reconcile_ack_uid, self.admin_user,
            'The acknowledgement records the actor, not the elevated user.',
        )
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        self.assertTrue(self.store._assert_export_reconciliation_complete())
        self.assertIn(
            'not cryptographically proven', self.store.export_reconcile_note,
            'A `complete` reached by acknowledgement must not read as a '
            'complete reached by proof.',
        )

    def test_the_binding_stays_in_review_after_acknowledgement(self):
        """The verdict is evidence and is never rewritten into a `verified`.

        Converging the STORE is the operator's decision; converting the
        BINDING's verdict to `verified` would be the connector claiming a
        proof it does not have, in the one field a later audit would read.
        """
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertEqual(
            self.binding.export_reconcile_reason, 'checksum_unverifiable',
        )

    def test_acknowledgement_is_idempotent(self):
        """Requirement 9."""
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.binding.invalidate_recordset()
        first_at = self.binding.export_reconcile_ack_at
        self.assertTrue(self._ack(user=self.admin_user))
        self.assertTrue(self._ack(user=self.admin_user))
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_ack_at, first_at)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    def test_acknowledgement_requires_the_explicit_confirmation(self):
        """Requirement 7: consent is an act, not a default."""
        self._reach_checksum_review()
        with self.assertRaises(UserError):
            self._ack(user=self.admin_user, confirmed=False)
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'review_required')

    def test_the_wizard_is_the_reachable_route_and_delegates(self):
        """The UI door is the same door, with the consequence copy attached."""
        self._reach_checksum_review()
        action = self.binding.with_user(self.admin_user).\
            action_shopify_export_open_checksum_ack_wizard()
        self.assertEqual(
            action['res_model'],
            'shopify.connector.export.checksum.ack.wizard',
        )
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()
        wizard.confirmed = True
        self.assertIn('no digest', wizard.unprovable_summary)
        self.assertIn(
            'does not verify anything', wizard.consequence_summary.lower(),
        )
        wizard.action_confirm()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    def test_the_wizard_copy_states_all_four_required_things(self):
        """Requirement 14, asserted on the copy an operator actually reads."""
        self._reach_checksum_review()
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        self.assertIn('still attached', wizard.verified_summary)
        self.assertIn('not archived', wizard.verified_summary)
        self.assertIn('FAILED', wizard.verified_summary)
        self.assertIn('no digest', wizard.unprovable_summary)
        self.assertIn('CANNOT prove', wizard.unprovable_summary)
        self.assertIn('accept', wizard.consequence_summary)
        self.assertIn('no export runs', wizard.consequence_summary)

    # ------------------------------------------------------------------
    # 3. Authority and company (SEC-3 negative axes)
    # ------------------------------------------------------------------

    def test_a_connector_user_is_refused(self):
        """Requirement 6. A Connector User implies Reviewer, so gating on
        Reviewer would have admitted exactly the role this refuses."""
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self._ack(user=self.connector_user)
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)

    def test_a_connector_user_cannot_open_the_wizard_either(self):
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self.binding.with_user(self.connector_user).\
                action_shopify_export_open_checksum_ack_wizard()

    def test_a_wrong_company_administrator_is_refused(self):
        """The company axis, observed with the role axis held constant."""
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self._ack(user=self.other_admin)
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'review_required')

    def test_a_foreign_record_id_supplied_directly_is_refused(self):
        """The RPC shape: an id typed into a call, not a record navigated to.

        `browse(id)` bypasses no ACL and proves nothing either -- which is
        why the production method calls `check_access` rather than trusting
        that the caller reached the record legitimately.
        """
        self._reach_checksum_review()
        foreign = self.TemplateBinding.with_user(self.other_admin).browse(
            self.binding.id,
        )
        with self.assertRaises(AccessError):
            foreign.action_shopify_export_acknowledge_checksum(confirmed=True)
        with self.assertRaises(AccessError):
            foreign.action_shopify_export_open_checksum_ack_wizard()

    def test_the_wizard_model_is_not_readable_by_a_connector_user(self):
        """The confirmation artifact is Administrator-only at the ACL, and
        that holds for the read/search surface, not only for `create()`.

        Correction A: this test used to assert only a `create()` refusal
        despite its name -- masked, harmlessly today, only by the model's
        single all-or-nothing ACL row. It now drives a real row into
        existence (as the Administrator who may legitimately do so) and
        proves a Connector User can neither read nor search it.
        """
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.connector_user).create({
                'binding_id': self.binding.id,
            })
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        with self.assertRaises(AccessError):
            wizard.with_user(self.connector_user).read(['store_id'])
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.connector_user).search(
                [('id', '=', wizard.id)],
            )

    # ------------------------------------------------------------------
    # 3b. Correction A: the wizard model boundary itself (Defect #1)
    # ------------------------------------------------------------------

    def test_a_cross_company_administrator_is_refused_before_any_content_returns(
        self,
    ):
        """The exact exploit named by independent-review Defect #1: a
        same-ROLE, cross-COMPANY Administrator calling `create({'binding_id':
        <foreign binding id>})` over plain RPC, no UI involved, then
        `read(['store_id', 'product_gid', 'reconcile_note'])`.

        The create is refused outright -- so there is no row a subsequent
        read could ever disclose anything through.
        """
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.other_admin).create({
                'binding_id': self.binding.id,
            })
        self.assertFalse(
            self.Wizard.with_user(self.other_admin).search([
                ('binding_id', '=', self.binding.id),
            ]),
            'The refused create() must not have left a row behind.',
        )

    def test_a_cross_company_administrator_cannot_disclose_through_default_context_opening(
        self,
    ):
        """The `default_get()`/context route -- the way the production
        action actually opens this wizard -- must refuse BEFORE the related
        display fields are ever computed against the foreign id, not only
        at `create()` time."""
        self._reach_checksum_review()
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.other_admin).with_context(
                active_model='shopify.connector.product.template.binding',
                active_id=self.binding.id,
            ).default_get(
                ['binding_id', 'store_id', 'product_gid', 'reconcile_note'],
            )

    def test_a_same_company_administrator_cannot_substitute_a_foreign_binding_via_write(
        self,
    ):
        """Create an allowed wizard, then try to retarget it at a binding
        outside the caller's company through `write()` -- the same
        disclosure Defect #1 named, reached through a different verb."""
        self._reach_checksum_review()
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        foreign_store = self.Store.sudo().create({
            'name': 'Correction A Foreign Store',
            'shop_domain': 'correction-a-foreign.myshopify.com',
            'api_version': self.store.api_version,
            'company_id': self.other_company.id,
        })
        foreign_binding = self.TemplateBinding.sudo().create({
            'store_id': foreign_store.id,
            'product_template_id': self.template.id,
            'shopify_gid': 'gid://shopify/Product/correction-a-foreign-1',
        })
        with self.assertRaises(AccessError):
            wizard.with_user(self.admin_user).write({
                'binding_id': foreign_binding.id,
            })

    def test_a_cross_company_administrator_cannot_read_or_search_another_companys_wizard_row(
        self,
    ):
        """A wizard row that legitimately exists must not be discoverable by
        another actor at all -- the creator-scoped rule, independent of and
        in addition to whichever company owns the underlying binding."""
        self._reach_checksum_review()
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        with self.assertRaises(AccessError):
            wizard.with_user(self.other_admin).read(
                ['store_id', 'product_gid', 'reconcile_note'],
            )
        self.assertFalse(
            self.Wizard.with_user(self.other_admin).search(
                [('id', '=', wizard.id)],
            ),
            'A wizard row belongs to the actor who opened it, not to every '
            'administrator who could theoretically read the model.',
        )

    def test_a_same_company_administrator_still_sees_an_authorized_wizard(
        self,
    ):
        """Positive control: none of the corrections above narrows the
        happy path. Same-company Administrator, same actor who created it,
        still sees exactly the display fields it should."""
        self._reach_checksum_review()
        wizard = self.Wizard.with_user(self.admin_user).create({
            'binding_id': self.binding.id,
        })
        self.assertEqual(wizard.store_id, self.store)
        self.assertEqual(wizard.product_gid, self.binding.shopify_gid)
        self.assertEqual(
            wizard.reconcile_note, self.binding.export_reconcile_note,
        )

    # ------------------------------------------------------------------
    # 4. Everything else stays blocked
    # ------------------------------------------------------------------

    def _assert_not_acknowledgeable(self, expected_reason):
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'review')
        self.assertEqual(
            self.binding.export_reconcile_reason, expected_reason,
        )
        with self.assertRaises(UserError):
            self._ack(user=self.admin_user)
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'A non-eligible review must keep the export block.',
        )

    def test_a_missing_product_cannot_be_acknowledged(self):
        self._associated_media_row()
        self._reconnect()
        self._run_pass(body=_product_body(exists=False))
        self._assert_not_acknowledgeable('product_missing')

    def test_an_archived_product_cannot_be_acknowledged(self):
        self._associated_media_row()
        self._reconnect()
        self._run_pass(body=_product_body(status='ARCHIVED'))
        self._assert_not_acknowledgeable('product_archived')

    def test_a_variant_divergence_cannot_be_acknowledged(self):
        self._associated_media_row()
        self._reconnect()
        self._run_pass(body=_product_body(variant_gids=()))
        self._assert_not_acknowledgeable('variant_divergence')

    def test_a_failed_media_file_cannot_be_acknowledged(self):
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=(FILE_GID,), status='FAILED'),
        )
        self._assert_not_acknowledgeable('media_failed_status')

    def test_a_detached_media_file_cannot_be_acknowledged(self):
        """The File still exists under this connector's filename, but is no
        longer on the product."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=()),
            files=_files_body(file_gids=(FILE_GID,)),
        )
        self._assert_not_acknowledgeable('media_absent')

    def test_a_vanished_media_file_cannot_be_acknowledged(self):
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=()), files=_files_body(file_gids=()),
        )
        self._assert_not_acknowledgeable('media_absent')

    def test_an_ambiguous_media_identity_cannot_be_acknowledged(self):
        """A File carrying this connector's filename under another id."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=()),
            files=_files_body(file_gids=('gid://shopify/MediaImage/OTHER',)),
        )
        self._assert_not_acknowledgeable('media_absent')

    def test_a_truncated_media_read_cannot_be_acknowledged(self):
        """Inconclusive evidence is never acknowledgeable: the connector did
        not see the whole list, so nothing about the missing part is known."""
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=('gid://shopify/MediaImage/OTHER',),
                              has_next=True),
        )
        self._assert_not_acknowledgeable('media_read_truncated')

    def test_a_truncated_read_cannot_be_acknowledged_even_when_every_claimed_file_is_present(
        self,
    ):
        """Correction C companion: the acknowledgement route itself.

        Not just the verdict -- an operator must never be able to accept
        "nothing was truncated" through the real acknowledgement action
        merely because every File this connector claims happened to land on
        the one page that was read.
        """
        self._associated_media_row()
        self._reconnect()
        self._run_pass(
            media=_media_body(file_gids=(FILE_GID,), has_next=True),
        )
        self._assert_not_acknowledgeable('media_read_truncated')

    def test_an_in_flight_media_upload_cannot_be_acknowledged(self):
        row = self._associated_media_row()
        row.sudo().write({'remote_status': 'staged'})
        self._reconnect()
        self._run_pass()
        self._assert_not_acknowledgeable('media_in_flight')

    def test_a_media_row_with_no_file_identity_cannot_be_acknowledged(self):
        row = self._associated_media_row()
        row.sudo().write({'shopify_gid': 'pending:abc'})
        self._reconnect()
        self._run_pass()
        self._assert_not_acknowledgeable('media_association_unrecorded')

    def test_a_verified_binding_has_nothing_to_acknowledge(self):
        self._reconnect()
        self._run_pass()
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'verified')
        with self.assertRaises(UserError):
            self._ack(user=self.admin_user)

    def test_a_foreign_store_identity_leaves_nothing_to_acknowledge(self):
        """A read that landed on another store records no verdict at all, so
        there is no review an acknowledgement could attach to."""
        self._associated_media_row()
        self._reconnect()
        job = self._reconcile_jobs().filtered(
            lambda j: j.state not in TERMINAL_JOB_STATES
        )[0]
        job.sudo().write({'state': 'running'})
        responder = self._responder(
            body=_product_body(shop_domain='someone-else.myshopify.com'),
        )
        with self.send_patch(responder):
            with self.assertRaises(JobHandlerError):
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.binding.invalidate_recordset()
        self.assertEqual(self.binding.export_reconcile_state, 'pending')
        with self.assertRaises(UserError):
            self._ack(user=self.admin_user)

    # ------------------------------------------------------------------
    # 5. The acknowledgement is bound to its evidence, and expires with it
    # ------------------------------------------------------------------

    def test_a_later_reconnect_invalidates_the_acknowledgement(self):
        """Requirement 8, first clause -- and the most important one."""
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        self._reconnect()
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())
        self.store.invalidate_recordset()
        self.assertIn(
            self.store.export_reconcile_state, RECONCILE_BLOCKING_STATES,
        )

    def test_a_changed_local_media_claim_invalidates_the_acknowledgement(self):
        """Requirement 8: a re-uploaded image is a different claim.

        The digest is over the identities AND the local checksum, so this
        does not need a mutation hook anywhere -- the acknowledgement simply
        stops matching what it accepted.
        """
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')
        row = self.MediaBinding.sudo().search([
            ('product_template_binding_id', '=', self.binding.id),
        ], limit=1)
        row.sudo().write({'odoo_image_checksum': 'a' * 64})
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())
        self.store.invalidate_recordset()
        # Caught by hand rather than with `assertRaises`. Odoo's
        # `TransactionCase.assertRaises` runs its block inside a savepoint and
        # ROLLS BACK when the exception fires (`odoo/tests/common.py`), which
        # would undo the very state change this test exists to observe.
        refused = False
        try:
            self.store._assert_export_reconciliation_complete()
        except UserError:
            refused = True
        self.assertTrue(refused, 'The export must be refused.')
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'An acknowledgement that stopped matching its evidence must '
            're-apply the export block, not keep releasing it.',
        )

    def test_a_changed_file_identity_invalidates_the_acknowledgement(self):
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        row = self.MediaBinding.sudo().search([
            ('product_template_binding_id', '=', self.binding.id),
        ], limit=1)
        row.sudo().write({'shopify_gid': 'gid://shopify/MediaImage/999'})
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())

    def test_a_changed_product_identity_invalidates_the_acknowledgement(self):
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.binding.sudo().write({'shopify_gid': 'gid://shopify/Product/999'})
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())

    def test_a_stale_generation_acknowledgement_is_refused(self):
        """Requirement 8: the evidence describes a connection that is gone."""
        self._reach_checksum_review()
        self.store.sudo().write({
            'export_reconcile_generation':
                self.store.export_reconcile_generation + 1,
        })
        self.store.invalidate_recordset()
        self.binding.invalidate_recordset()
        with self.assertRaises(UserError):
            self._ack(user=self.admin_user)

    def test_a_new_verdict_drops_any_previous_acknowledgement(self):
        """A pass that ran again is evidence nobody has accepted yet."""
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        self.binding.invalidate_recordset()
        self.assertTrue(self.binding.export_reconcile_ack_at)
        self.Reconcile._record_binding_verdict(
            self.binding, 'review', 'A fresh, different finding.',
            reason='media_absent',
            generation=self.store.export_reconcile_generation,
        )
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding.export_reconcile_ack_at)
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())

    # ------------------------------------------------------------------
    # 6. Per-binding isolation and store convergence
    # ------------------------------------------------------------------

    def _second_media_binding(self):
        template = self.env['product.template'].create({
            'name': 'Second media widget',
            'shopify_export_enabled': True,
        })
        binding = self.TemplateBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_id': template.id,
            'shopify_gid': 'gid://shopify/Product/SECOND',
        })
        checksum = image_checksum(base64.b64decode(PNG_1X1) + b'second')
        self.MediaBinding.sudo().create({
            'store_id': self.store.id,
            'product_template_binding_id': binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': self.Media._connector_filename(
                template.id, checksum,
            ),
            'shopify_gid': 'gid://shopify/MediaImage/SECOND',
            'remote_status': 'associated',
        })
        return binding

    def test_acknowledging_one_binding_does_not_clear_another(self):
        """Requirements 12 and 13, together."""
        second = self._second_media_binding()
        self._associated_media_row()
        self._reconnect()
        self._run_pass(media=_media_body(
            file_gids=(FILE_GID, 'gid://shopify/MediaImage/SECOND'),
        ))
        self.binding.invalidate_recordset()
        second.invalidate_recordset()
        self.assertEqual(
            self.binding.export_reconcile_reason, 'checksum_unverifiable')
        self.assertEqual(
            second.export_reconcile_reason, 'checksum_unverifiable')

        self._ack(user=self.admin_user)
        second.invalidate_recordset()
        self.store.invalidate_recordset()
        self.assertFalse(
            second.export_reconcile_ack_at,
            'One binding\'s acknowledgement may never touch another\'s.',
        )
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'An outstanding review keeps the block.',
        )

        self._ack(user=self.admin_user, binding=second)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    def test_an_unresolved_non_eligible_binding_keeps_the_block(self):
        """A store converges only when EVERY binding is verified or validly
        acknowledged -- an acknowledgeable one next to a missing product
        stays blocked."""
        second = self._second_media_binding()
        self._associated_media_row()
        self._reconnect()
        jobs = self._reconcile_jobs().filtered(
            lambda j: j.state not in TERMINAL_JOB_STATES
        )
        for job in jobs:
            gone = job.res_id == second.id
            responder = self._responder(
                body=_product_body(exists=False) if gone else _product_body(),
                media=_media_body(file_gids=(FILE_GID,)),
            )
            with self.send_patch(responder):
                job.sudo().write({'state': 'running'})
                self.Reconcile._handle_product_export_reconnect_reconcile(job)
        self.binding.invalidate_recordset()
        second.invalidate_recordset()
        self.assertEqual(second.export_reconcile_reason, 'product_missing')
        self._ack(user=self.admin_user)
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_state, 'review_required',
            'The one binding nobody can acknowledge still blocks the store.',
        )
        with self.assertRaises(UserError):
            self.store._assert_export_reconciliation_complete()

    def test_the_store_review_list_surfaces_exactly_the_open_reviews(self):
        """The list the store form renders is the work, and it is bounded."""
        self._reach_checksum_review()
        self.store.invalidate_recordset()
        self.assertEqual(
            self.store.export_reconcile_review_binding_ids, self.binding,
        )
        source = inspect.getsource(
            self.env['shopify.connector.store'].
            _compute_export_reconcile_review_binding_ids.__func__
        )
        self.assertIn(
            'limit=EXPORT_RECONCILE_REVIEW_LIMIT', source,
            'The review list must be a bounded read.',
        )

    def test_the_review_list_is_company_isolated(self):
        """A foreign administrator reads an EMPTY list, never a filtered one.

        The compute runs as the calling user, so the SEC-3 binding rule
        decides what it can contain. That is what makes the count safe too: a
        list that is empty rather than shortened discloses nothing about how
        many reviews another company has outstanding.
        """
        self._reach_checksum_review()
        foreign_store = self.store.with_user(self.other_admin).with_context(
            allowed_company_ids=self.other_company.ids,
        )
        self.assertFalse(
            foreign_store.export_reconcile_review_binding_ids,
            'Another company\'s outstanding reviews must not be reachable '
            'through the store form projection.',
        )
        # The owning administrator, by contrast, sees it -- without which the
        # assertion above could pass because the list is broken for everyone.
        self.assertEqual(
            self.store.with_user(self.admin_user)
            .export_reconcile_review_binding_ids,
            self.binding,
        )
        # And the binding row itself is unreachable, not merely unlisted.
        foreign_binding = self.TemplateBinding.with_user(
            self.other_admin,
        ).with_context(
            allowed_company_ids=self.other_company.ids,
        ).browse(self.binding.id)
        with self.assertRaises(AccessError):
            foreign_binding.export_reconcile_reason

    def test_the_review_list_is_not_cached_across_users(self):
        """A defect this cycle found and fixed, kept as a regression.

        Odoo caches a non-stored computed field ONCE PER RECORD for the whole
        transaction unless the field declares the context it depends on
        (`Environment.cache_key`). This list is produced by a search the
        caller's record rules filter, so without `depends_context` the first
        reader's result is handed to the second -- and the dangerous
        direction is owner-first: the foreign administrator would then read
        the OWNER's outstanding reviews out of the cache.

        Asserted in BOTH orders, because a single order can pass by accident.
        """
        self._reach_checksum_review()
        owner_view = self.store.with_user(self.admin_user)
        foreign_view = self.store.with_user(self.other_admin).with_context(
            allowed_company_ids=self.other_company.ids,
        )
        # Owner first, then foreign.
        self.assertEqual(
            owner_view.export_reconcile_review_binding_ids, self.binding)
        self.assertFalse(
            foreign_view.export_reconcile_review_binding_ids,
            'The foreign administrator read the owner\'s list out of a '
            'shared field cache.',
        )
        # Foreign first, then owner, on a fresh cache.
        self.env.invalidate_all()
        self.assertFalse(
            foreign_view.export_reconcile_review_binding_ids)
        self.assertEqual(
            owner_view.export_reconcile_review_binding_ids, self.binding,
            'The owner read the foreign administrator\'s empty list out of a '
            'shared field cache.',
        )

    # ------------------------------------------------------------------
    # 7. Nothing reaches Shopify, and nothing writes a protected field
    # ------------------------------------------------------------------

    def test_no_transport_occurs_during_an_acknowledgement(self):
        """Requirement 10, observed rather than asserted from the source.

        The transport seam is patched with a responder that FAILS the test if
        it is reached at all, so a request of any kind -- read or mutation --
        would be caught, not merely a mutation.
        """
        self._reach_checksum_review()

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError(
                'The acknowledgement route contacted Shopify: %r'
                % ((request or {}).get('query') or '')[:120]
            )

        with self.send_patch(refuse):
            self._ack(user=self.admin_user)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')

    def test_the_acknowledgement_route_contains_no_transport_or_mutation(self):
        """Requirement 10, on the source of the route itself."""
        source = ''.join(
            inspect.getsource(func) for func in (
                self.TemplateBinding.
                action_shopify_export_acknowledge_checksum.__func__,
                self.TemplateBinding.
                _assert_export_reconcile_ack_eligible.__func__,
                self.TemplateBinding.
                _assert_export_reconcile_ack_authority.__func__,
            )
        )
        for forbidden in (
            '_send', '_read_remote_product', '_read_remote_product_media',
            '_search_remote_files_by_filename', '_enqueue', '_admit',
            'productUpdate', 'fileDelete', 'productCreateMedia',
        ):
            self.assertNotIn(
                forbidden, source,
                'The acknowledgement must not be able to reach Shopify or '
                'admit a job; it names %s.' % forbidden,
            )

    def test_the_acknowledgement_fields_are_protected_from_direct_writes(self):
        """Anti-spoof: the fields the validity check reads are exactly the
        fields a caller must not be able to set."""
        self._reach_checksum_review()
        protected = self.TemplateBinding._protected_binding_fields()
        for name in (
            'export_reconcile_reason',
            'export_reconcile_evidence_generation',
            'export_reconcile_evidence_product_gid',
            'export_reconcile_evidence_file_gids',
            'export_reconcile_evidence_claim_digest',
            'export_reconcile_ack_at',
            'export_reconcile_ack_uid',
            'export_reconcile_ack_reason',
            'export_reconcile_ack_generation',
            'export_reconcile_ack_product_gid',
            'export_reconcile_ack_file_gids',
            'export_reconcile_ack_claim_digest',
            'export_reconcile_ack_verdict_at',
        ):
            self.assertIn(name, protected)
        with self.assertRaises(AccessError):
            self.binding.with_user(self.admin_user).write({
                'export_reconcile_ack_at': fields.Datetime.now(),
            })
        with self.assertRaises(AccessError):
            self.binding.with_user(self.admin_user).write({
                'export_reconcile_reason': 'checksum_unverifiable',
            })

    def test_a_forged_acknowledgement_still_fails_validation(self):
        """Defence in depth: even a superuser-forged ack that does not match
        the evidence is not honoured.

        `sudo()` bypasses the protected-field guard by design -- connector
        system code needs it. So the validity check re-derives every bound
        value instead of trusting the stored flag, and this is that claim.
        """
        self._reach_checksum_review()
        self.binding.sudo().write({
            'export_reconcile_ack_at': fields.Datetime.now(),
            'export_reconcile_ack_uid': self.admin_user.id,
            'export_reconcile_ack_reason': 'checksum_unverifiable',
            'export_reconcile_ack_generation':
                self.store.export_reconcile_generation,
            'export_reconcile_ack_product_gid': self.binding.shopify_gid,
            'export_reconcile_ack_file_gids': 'gid://shopify/MediaImage/FORGED',
            'export_reconcile_ack_claim_digest': 'not-a-real-digest',
            'export_reconcile_ack_verdict_at': self.binding.export_reconcile_at,
        })
        self.binding.invalidate_recordset()
        self.assertFalse(self.binding._export_reconcile_ack_is_valid())
        self.store.sudo().write({'export_reconcile_state': 'review_required'})
        self.store._settle_export_reconciliation(
            generation=self.store.export_reconcile_generation,
        )
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'review_required')

    # ------------------------------------------------------------------
    # 8. Audit
    # ------------------------------------------------------------------

    def test_the_acknowledgement_is_audited_with_the_actor(self):
        """Requirement 7: who, when, and the governed consequence."""
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        self._reach_checksum_review()
        self._ack(user=self.admin_user)
        audits = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ], order='id desc')
        self.assertEqual(len(audits) - before, 1)
        logs = self.env['shopify.connector.job.log'].sudo().search([
            ('job_id', '=', audits[0].id),
        ])
        message = ' '.join(logs.mapped('message') or [])
        self.assertIn('acknowledged', message)
        self.assertIn('actor_uid=%d' % self.admin_user.id, message)
        self.assertIn('NOT', message)
        self.assertNotIn(DUMMY_TOKEN, message)
        self.assertNotIn(
            DUMMY_TOKEN,
            ' '.join(str(v) for v in logs.mapped('payload_snapshot') if v),
        )

    # ------------------------------------------------------------------
    # 6. Complete acknowledgement revalidation (Correction D)
    # ------------------------------------------------------------------

    def _create_valid_acknowledged_review_bindings(
        self, count, gid_prefix, generation, verdict_at,
    ):
        """Bulk-construct `count` bindings whose acknowledgement is valid.

        Bypasses the job/transport pipeline deliberately: that pipeline is
        exercised elsewhere in this file, and re-running it hundreds of
        times per test would make a >200-row scale regression prohibitively
        slow. What THIS test exists to prove is that the real revalidation
        route (`_reassert_export_reconcile_acknowledgements`, through
        `_assert_export_reconciliation_complete`) walks every matching row
        rather than the first `EXPORT_RECONCILE_REVIEW_LIMIT` of them -- so
        each row is written, through `sudo()`, with the exact evidence and
        acknowledgement fields `_export_reconcile_ack_is_valid` requires to
        agree (no associated media rows are created, so every claim is the
        empty-media claim; the digest below is computed the same way
        `_export_reconcile_claim_digest` computes it).
        """
        Binding = self.TemplateBinding
        # `(store_id, product_template_id)` is UNIQUE
        # (`_store_product_template_uniq`), so a scale fixture needs a
        # distinct product per row, not `self.template` reused `count`
        # times.
        templates = self.env['product.template'].create([
            {'name': 'Scale fixture %s %d' % (gid_prefix, index)}
            for index in range(count)
        ])
        vals_list = []
        for index, template in enumerate(templates):
            gid = 'gid://shopify/Product/%s-%d' % (gid_prefix, index)
            digest = hashlib.sha256(
                json.dumps(
                    {'product_gid': gid, 'media': []},
                    sort_keys=True, separators=(',', ':'),
                ).encode('utf-8'),
            ).hexdigest()
            vals_list.append({
                'store_id': self.store.id,
                'product_template_id': template.id,
                'shopify_gid': gid,
                'export_reconcile_state': 'review',
                'export_reconcile_reason': 'checksum_unverifiable',
                'export_reconcile_at': verdict_at,
                'export_reconcile_evidence_generation': generation,
                'export_reconcile_evidence_product_gid': gid,
                'export_reconcile_evidence_file_gids': '',
                'export_reconcile_evidence_claim_digest': digest,
                'export_reconcile_ack_at': verdict_at,
                'export_reconcile_ack_uid': self.admin_user.id,
                'export_reconcile_ack_reason': 'checksum_unverifiable',
                'export_reconcile_ack_generation': generation,
                'export_reconcile_ack_product_gid': gid,
                'export_reconcile_ack_file_gids': '',
                'export_reconcile_ack_claim_digest': digest,
                'export_reconcile_ack_verdict_at': verdict_at,
            })
        bindings = Binding.sudo().create(vals_list)
        for binding in bindings:
            self.assertTrue(
                binding._export_reconcile_ack_is_valid(),
                'Fixture bug: the constructed acknowledgement must be valid '
                'before it is tampered with.',
            )
        return bindings

    def test_a_stale_acknowledgement_beyond_two_hundred_is_still_reached(
        self,
    ):
        """Correction D (independent review, Defect #5), stated as a test.

        More than `EXPORT_RECONCILE_REVIEW_LIMIT` (200) acknowledged review
        bindings exist for one store; one stale acknowledgement sits well
        beyond the 200th by id -- the exact position the predecessor's
        bounded, unordered 200-row search could never reach. The REAL
        production route must still find it, re-block the store, and leave
        every other binding's valid acknowledgement untouched.
        """
        count = RECONCILE_REVALIDATION_BATCH_SIZE + 20
        generation = 7
        verdict_at = fields.Datetime.now()
        self.store.sudo().write({
            'export_reconcile_state': 'complete',
            'export_reconcile_generation': generation,
        })
        bindings = self._create_valid_acknowledged_review_bindings(
            count, 'stale-scale', generation, verdict_at,
        )
        stale = bindings[209]
        others = bindings - stale
        stale.sudo().write({
            'export_reconcile_ack_product_gid': 'gid://shopify/Product/tampered',
        })
        self.assertFalse(stale._export_reconcile_ack_is_valid())
        # Hand-caught rather than `assertRaises`: the block below writes
        # `export_reconcile_state` to the database before it raises, and
        # `TransactionCase.assertRaises` rolls back its savepoint on the
        # caught exception, which would undo the very write this test
        # exists to observe (see
        # `test_a_changed_local_media_claim_invalidates_the_acknowledgement`
        # above for the same pattern).
        refused = False
        try:
            self.store._assert_export_reconciliation_complete()
        except UserError:
            refused = True
        self.assertTrue(
            refused,
            'A stale acknowledgement beyond the old 200-row cutoff must '
            'still re-block exports.',
        )
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'review_required')
        stale.invalidate_recordset()
        self.assertEqual(
            stale.export_reconcile_state, 'review',
            'Revalidation records nothing on the binding itself; only the '
            'store verdict moves.',
        )
        for binding in others:
            binding.invalidate_recordset()
            self.assertTrue(
                binding._export_reconcile_ack_is_valid(),
                'A stale sibling must never corrupt another binding\'s '
                'still-valid acknowledgement.',
            )

    def test_a_fully_valid_population_beyond_two_hundred_stays_complete(
        self,
    ):
        """The pagination fix must not become a vacuous permanent block.

        Every binding beyond the 200th (by id) is genuinely still valid, so
        walking the whole set must converge on `complete`, not on a refusal
        manufactured merely by touching every row.
        """
        count = RECONCILE_REVALIDATION_BATCH_SIZE + 20
        generation = 11
        verdict_at = fields.Datetime.now()
        self.store.sudo().write({
            'export_reconcile_state': 'complete',
            'export_reconcile_generation': generation,
        })
        self._create_valid_acknowledged_review_bindings(
            count, 'valid-scale', generation, verdict_at,
        )
        self.assertTrue(self.store._assert_export_reconciliation_complete())
        self.store.invalidate_recordset()
        self.assertEqual(self.store.export_reconcile_state, 'complete')


#: The dispatcher logs the SQLSTATE it observed before recovering. That line is
#: the only place the exact PostgreSQL error code surfaces as evidence, so the
#: race proofs below read it rather than asserting the recovery happened "for
#: some reason".
DISPATCH_LOGGER = (
    'odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch'
)


# Non-standard, and for one reason: the boundary under test IS a PostgreSQL
# serialization failure, and a serialization failure cannot occur on the single
# shared in-test connection -- one transaction does not conflict with itself.
# This class therefore needs GENUINE independent pooled connections with real
# commit boundaries. It is bounded (statement_timeout + lock_timeout), creates
# its own store, cleans up its committed fixtures and asserts zero residue. The
# suite runner runs it by tag.
@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_export_reconcile_race')
class TestExportReconnectSettlementRace(TransactionCase):
    """TD-015 settlement, proved ACROSS transactions instead of within one.

    What was missing, and why it mattered
    -------------------------------------
    `TestExportReconnectConvergence` covers ordering, the terminal-set
    invariant and generation binding -- all of it inside the single shared
    `TransactionCase` cursor, where each job's write is already visible to
    the next. That is real coverage of the *decision*, and it is no
    coverage at all of the *mechanism*: the correction's entire claim is
    that a concurrent settlement raises `40001` and is re-driven, and a
    transaction cannot raise `40001` against itself. The previous cycle's
    records nevertheless said the proof used "two genuine pooled
    connections". It did not. This class is that proof.

    The interleaving, and why it is deterministic
    ---------------------------------------------
    No threads, no sleeps, no barrier -- the race is *stepped* by the
    transport seam, so it runs identically every time:

    1. **Worker A** runs the production `run_drain(1)` on its own pooled
       connection. It claims the lower-id reconcile job, starts it, and
       reaches `_send` for its product read.
    2. **Inside that `_send`**, worker B opens a second, independent pooled
       connection and runs the production handler for the *other* reconcile
       job -- same store, same generation -- to completion, and commits. B
       bumps the store's settlement sequence, reads its siblings, sees A's
       binding still `pending` (A has committed nothing), and correctly
       declines to settle. The store is still `in_progress`.
    3. A's `_send` returns. A records its own verdict, flushes it, and
       reaches `_serialize_reconcile_settlement` -- an `UPDATE` of a store
       row that B committed an `UPDATE` to *after A's snapshot was taken*.
       Under REPEATABLE READ that is a genuine SQLSTATE `40001`.
    4. The real `_drain_one` catches it, rolls back, re-locks the job, and
       routes it once through its declared `remote_read_replay_safe` policy
       to a bounded `concurrency_race_conflict` retry. The handler is never
       replayed.
    5. The retry is made due and the **production dispatcher re-drives the
       job on a fresh connection and a fresh snapshot**, where B's verdict
       is now visible. It settles, and the store converges.

    Step 3 is the whole point, and `test_without_the_serialization_
    boundary_the_store_is_stranded` proves it by removing exactly that one
    thing and running the identical interleaving: with no conflict, A reads
    its siblings from its own stale snapshot, sees B's binding still
    `pending`, declines as well -- and both jobs commit `succeeded`, every
    binding terminal, the store permanently `in_progress`. The old defect,
    reproduced on demand.

    Why B runs the handler rather than a second `run_drain`
    -------------------------------------------------------
    It cannot run a second `run_drain`, and that is a property of the
    production claim rather than a shortcut here. `_drain_one` claims via
    `_claim_for_dispatch(1)`, which searches `order='id asc', limit=1` and
    then `try_lock_for_update()` -- `FOR UPDATE SKIP LOCKED` at the pinned
    Odoo 19 commit. A second worker facing a locked lowest-id candidate
    locks nothing and claims nothing. That is asserted directly by
    `test_a_second_worker_cannot_claim_past_a_locked_job`, and it is why B
    drives the production handler inside its own genuine transaction while
    A -- the side that must observe the conflict and recover -- runs the
    complete production dispatcher.

    Zero Shopify contact: `_send` is replaced, so the real client, the real
    admission and the real response taxonomy all run and only the socket is
    absent.
    """

    STATEMENT_TIMEOUT_MS = 20000
    LOCK_TIMEOUT_MS = 10000

    # ------------------------------------------------------------------
    # Genuine-connection plumbing
    # ------------------------------------------------------------------

    def _open_bounded(self):
        """A real pooled cursor carrying both transaction-local PG limits.

        Bounded so this test fails closed. Without them a proof about lock
        conflicts is one deadlock away from hanging the whole suite, which
        reports as neither pass nor fail.
        """
        cr = db_connect(self.env.cr.dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _backend_pid(self, cr):
        cr.execute('SELECT pg_backend_pid()')
        return cr.fetchone()[0]

    def _real_registry_cursor(self):
        """`registry.cursor()` handing out bounded real pooled cursors.

        Production opens its admission/lease side transaction on
        `registry.cursor()`. In test mode that is a `TestCursor` sharing the
        single test connection -- which would quietly re-join the two
        workers this class exists to keep apart.
        """
        return lambda *args, **kwargs: self._open_bounded()

    @contextlib.contextmanager
    def _capture_dispatch_log(self):
        """Collect the dispatcher's records without requiring any.

        `assertLogs` fails when nothing is logged, and the sensitivity case
        below asserts precisely that nothing was -- so it cannot be used
        here. The handler class is local rather than module-level because
        `test_export_source_guards.py::test_every_test_class_declares_its_
        phase` walks every top-level class in this directory and requires a
        phase declaration; a logging helper is not a test class and must not
        pretend to be one to satisfy the guard.
        """
        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Capture(level=logging.INFO)
        logger = logging.getLogger(DISPATCH_LOGGER)
        logger.addHandler(handler)
        previous = logger.level
        logger.setLevel(logging.INFO)
        try:
            yield records
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous)

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _commit_fixture(self):
        """A connected store with TWO exported bindings and one live pass.

        Committed on its own connection, because both workers below must be
        able to see it from transactions this one does not own.
        """
        suffix = uuid.uuid4().hex[:8]
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            shop_domain = 'td015-race-%s.myshopify.com' % suffix
            store = env['shopify.connector.store'].create({
                'name': 'TD-015 race store %s' % suffix,
                'shop_domain': shop_domain,
                'api_version': SHOPIFY_API_VERSION,
                'state': 'connected',
            })
            # `execute_business` refuses a connected store with no usable
            # token before `_send`, so without a credential neither worker
            # would reach the settlement boundary at all.
            env['shopify.connector.store.credential'].create({
                'store_id': store.id,
                'access_token': DUMMY_TOKEN,
            })
            store.write({'state': 'connected'})
            env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'product_export_domain_enabled': True,
                'price_source_of_truth': 'odoo_authoritative',
            })
            template_ids, binding_ids, gids = [], [], {}
            for index in (1, 2):
                template = env['product.template'].create({
                    'name': 'TD-015 race widget %s-%d' % (suffix, index),
                    'shopify_export_enabled': True,
                })
                gid = 'gid://shopify/Product/TD015RACE%s%d' % (suffix, index)
                binding = env[
                    'shopify.connector.product.template.binding'
                ].create({
                    'store_id': store.id,
                    'product_template_id': template.id,
                    'shopify_gid': gid,
                })
                template_ids.append(template.id)
                binding_ids.append(binding.id)
                gids[binding.id] = gid
            # The real reconnect entry point: it expires open previews,
            # marks every exported binding `pending`, blocks exports and
            # enqueues one job per binding at the store's current epoch.
            store._require_export_reconnect_reconciliation()
            env.flush_all()
            jobs = env['shopify.connector.job'].search([
                ('store_id', '=', store.id),
                ('job_type', '=', JOB_TYPE_RECONNECT_RECONCILE),
            ], order='id asc')
            self.assertEqual(
                len(jobs), 2,
                'The race needs exactly two final reconciliation jobs for '
                'one store and one generation.',
            )
            fixture = {
                'store_id': store.id,
                'shop_domain': shop_domain,
                'generation': store.connection_generation,
                # A claims the LOWEST id -- `_claim_for_dispatch` searches
                # `order='id asc', limit=1` -- so B must take the other one.
                'job_a_id': jobs[0].id,
                'job_b_id': jobs[1].id,
                'binding_a_id': jobs[0].res_id,
                'binding_b_id': jobs[1].res_id,
                'gid_a': gids[jobs[0].res_id],
                'gid_b': gids[jobs[1].res_id],
                'template_ids': template_ids,
            }
            self.assertEqual(
                store.export_reconcile_state, 'in_progress',
                'Exports must be blocked before the race starts, or the '
                'convergence assertions prove nothing.',
            )
            cr.commit()
            # Registered the moment the rows are durable, so a failure in
            # the precondition below still tears the fixture down.
            self.addCleanup(self._cleanup_and_assert_no_residue, fixture)
            self._assert_no_competing_claimable(cr, fixture)
            cr.rollback()
        finally:
            cr.close()
        return fixture

    def _assert_no_competing_claimable(self, cr, fixture):
        """No foreign job may sit ahead of ours in the claim order.

        `_claim_for_dispatch` searches the WHOLE job table `order='id asc',
        limit=1`. A committed, claimable job belonging to some other test
        with a lower id would be the one `run_drain` picks, and this class's
        race would silently never happen. Every genuine-connection harness
        in this repository cleans up its committed jobs for exactly this
        reason, so this is a fail-closed precondition rather than an
        expected outcome -- if it ever fires, a harness leaked rows.
        """
        cr.execute(
            "SELECT id, store_id, state FROM shopify_connector_job "
            "WHERE id < %s AND store_id != %s AND ("
            "  state = 'queued' OR ("
            "    state = 'retry_waiting' AND next_retry_at <= now()))"
            " ORDER BY id LIMIT 5",
            (fixture['job_a_id'], fixture['store_id']),
        )
        competing = cr.fetchall()
        self.assertEqual(
            competing, [],
            'Another test left claimable jobs committed ahead of this '
            'fixture, so run_drain would claim one of them instead of the '
            'race job: %r' % (competing,),
        )

    def _cleanup_and_assert_no_residue(self, fixture):
        """Remove this test's COMMITTED rows, then prove they are gone.

        `TransactionCase` rolls back its own cursor; it cannot roll back
        what these workers committed on connections it does not own. Job
        logs are append-only and jobs cannot be unlinked through the ORM,
        so the teardown is raw SQL scoped to this one store id, in
        foreign-key order.
        """
        store_id = fixture['store_id']
        cr = self._open_bounded()
        try:
            cr.execute(
                'UPDATE shopify_connector_job SET mutation_attempt_id = NULL '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job_log WHERE job_id IN '
                '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
                (store_id,),
            )
            for table in (
                'shopify_connector_mutation_attempt',
                'shopify_connector_call_lease',
                'shopify_connector_job',
                'shopify_connector_product_export_preview',
                'shopify_connector_product_media_binding',
                'shopify_connector_product_variant_binding',
                'shopify_connector_product_template_binding',
                'shopify_connector_store_settings',
                'shopify_connector_store_credential',
            ):
                # Fixed literal tuple in this file; the only interpolated
                # value is the parameterised store id.
                cr.execute(
                    'DELETE FROM ' + table + ' WHERE store_id = %s',
                    (store_id,),
                )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()
        finally:
            cr.close()

        # The templates go through the ORM, so anything that legitimately
        # references them refuses loudly rather than leaving a dangling row.
        drop = self._open_bounded()
        try:
            env = api.Environment(drop, SUPERUSER_ID, {})
            env['product.template'].browse(fixture['template_ids']).unlink()
            drop.commit()
        finally:
            drop.close()

        check = self._open_bounded()
        try:
            residue = {}
            for table in (
                'shopify_connector_job',
                'shopify_connector_call_lease',
                'shopify_connector_product_template_binding',
                'shopify_connector_product_media_binding',
                'shopify_connector_store_credential',
                'shopify_connector_store_settings',
            ):
                check.execute(
                    'SELECT count(*) FROM ' + table + ' WHERE store_id = %s',
                    (store_id,),
                )
                residue[table] = check.fetchone()[0]
            check.execute(
                'SELECT count(*) FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            residue['shopify_connector_store'] = check.fetchone()[0]
            check.execute(
                'SELECT count(*) FROM product_template WHERE id IN %s',
                (tuple(fixture['template_ids']),),
            )
            residue['product_template'] = check.fetchone()[0]
            check.rollback()
        finally:
            check.close()
        self.assertEqual(
            set(residue.values()), {0},
            'The race left committed test residue behind: %r' % residue,
        )

    # ------------------------------------------------------------------
    # The stepped interleaving
    # ------------------------------------------------------------------

    def _responder(self, fixture, trace, missing_gid=None, run_sibling=True):
        """One transport stand-in that also STEPS the race.

        The sibling transaction is launched from inside worker A's first
        `_send`, which is what makes the interleaving deterministic without
        a sleep, a thread or a barrier: A is provably mid-handler and
        provably has not committed when B runs.
        """
        def responder(_self, _store, request, token=None,
                      mutation_context=None):
            query = (request or {}).get('query') or ''
            requested = ((request or {}).get('variables') or {}).get('id')
            trace.setdefault('queries', []).append(query.split('(')[0].strip())
            if run_sibling and not trace.get('sibling_ran'):
                trace['sibling_ran'] = True
                self._run_sibling(fixture, responder, trace)
            body = _product_body(
                exists=(requested != missing_gid),
                variant_gids=(),
                shop_domain=fixture['shop_domain'],
            )
            if body['data']['product'] is not None:
                body['data']['product']['id'] = requested
            return FakeSendResponse(body)
        return responder

    def _run_sibling(self, fixture, responder, trace):
        """Worker B: the OTHER final job, in its own genuine transaction."""
        cr = self._open_bounded()
        try:
            trace['sibling_pid'] = self._backend_pid(cr)
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(fixture['job_b_id'])
            job.write({'state': 'running'})
            env[
                'shopify.connector.export.reconcile.service'
            ]._handle_product_export_reconnect_reconcile(job)
            env.flush_all()
            # Committed BEFORE worker A reaches its own settlement boundary.
            # This commit is the concurrent update A's snapshot cannot see.
            cr.commit()
            trace['sibling_settled_state'] = env[
                'shopify.connector.store'
            ].browse(fixture['store_id']).export_reconcile_state
        finally:
            cr.close()

    def _drain_once(self, fixture, trace, missing_gid=None, bypass=False,
                    run_sibling=True):
        """Worker A: the complete production dispatcher on a real connection."""
        ClientCls = type(self.env['shopify.connector.api.client'])
        StoreCls = type(self.env['shopify.connector.store'])
        responder = self._responder(
            fixture, trace, missing_gid=missing_gid, run_sibling=run_sibling,
        )
        cr = self._open_bounded()
        try:
            trace['drain_pid'] = self._backend_pid(cr)
            cr.execute('SHOW transaction_isolation')
            self.assertEqual(
                cr.fetchone()[0], 'repeatable read',
                'The drain cursor must run at the production isolation level '
                '-- 40001 is a REPEATABLE READ phenomenon.',
            )
            env = api.Environment(cr, SUPERUSER_ID, {})
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(
                    self.registry, 'cursor', self._real_registry_cursor(),
                ))
                stack.enter_context(patch.object(
                    ClientCls, '_send', responder,
                ))
                if bypass:
                    # The sensitivity lever, and ONLY this. Everything else
                    # -- the verdict write, the flush, the sibling read, the
                    # decision -- stays exactly as production runs it.
                    stack.enter_context(patch.object(
                        StoreCls, '_serialize_reconcile_settlement',
                        lambda store_self: True,
                    ))
                records = stack.enter_context(self._capture_dispatch_log())
                env['shopify.connector.job.dispatch'].run_drain(1)
                trace['log'] = [
                    record.getMessage() for record in records
                ]
            cr.commit()
        finally:
            cr.close()
        return trace

    def _observe(self, fixture):
        """Read the COMMITTED state on a third, independent connection."""
        cr = self._open_bounded()
        try:
            cr.execute(
                'SELECT export_reconcile_state, export_reconcile_generation, '
                'export_reconcile_settle_seq FROM shopify_connector_store '
                'WHERE id = %s', (fixture['store_id'],),
            )
            state, generation, settle_seq = cr.fetchone()
            cr.execute(
                'SELECT id, export_reconcile_state FROM '
                'shopify_connector_product_template_binding '
                'WHERE store_id = %s', (fixture['store_id'],),
            )
            bindings = dict(cr.fetchall())
            cr.execute(
                'SELECT id, state, error_class FROM shopify_connector_job '
                'WHERE store_id = %s', (fixture['store_id'],),
            )
            jobs = {row[0]: (row[1], row[2]) for row in cr.fetchall()}
            cr.rollback()
        finally:
            cr.close()
        return {
            'state': state, 'generation': generation,
            'settle_seq': settle_seq, 'bindings': bindings, 'jobs': jobs,
        }

    def _make_retry_due(self, fixture):
        """Advance the bounded retry's clock -- nothing else.

        The dispatcher's own claim predicate (`retry_waiting` AND
        `next_retry_at <= now`) is left to decide whether the job is
        claimable; this only removes the wall-clock wait.
        """
        cr = self._open_bounded()
        try:
            cr.execute(
                'SELECT state FROM shopify_connector_job WHERE id = %s',
                (fixture['job_a_id'],),
            )
            self.assertEqual(
                cr.fetchone()[0], 'retry_waiting',
                'The conflicted job must be sitting in a bounded retry for '
                'the dispatcher to re-drive it.',
            )
            cr.execute(
                "UPDATE shopify_connector_job SET next_retry_at = "
                "now() - interval '1 minute' WHERE id = %s",
                (fixture['job_a_id'],),
            )
            cr.commit()
            self._assert_no_competing_claimable(cr, fixture)
            cr.rollback()
        finally:
            cr.close()

    def _assert_genuine_conflict(self, trace, observed, job_a_id):
        """The conflict itself, asserted rather than inferred."""
        self.assertNotEqual(
            trace['drain_pid'], trace['sibling_pid'],
            'The two transactions must run on distinct PostgreSQL backends.',
        )
        self.assertEqual(
            trace.get('sibling_settled_state'), 'in_progress',
            'Worker B must correctly DECLINE to settle: it cannot see A\'s '
            'verdict, so it is not the last job. This is the exact race '
            'shape that used to strand the store.',
        )
        conflict = [
            message for message in trace['log']
            if 'PostgreSQL concurrency failure' in message
        ]
        self.assertTrue(
            conflict,
            'The dispatcher never reported a concurrency failure, so no '
            'serialization boundary was reached. Log: %r' % trace['log'],
        )
        self.assertIn(
            'SQLSTATE %s' % psycopg2.errorcodes.SERIALIZATION_FAILURE,
            conflict[0],
            'The conflict must be a genuine 40001 (serialization failure), '
            'not a lock timeout or an injected exception: %r' % conflict,
        )
        state, error_class = observed['jobs'][job_a_id]
        self.assertEqual(
            state, 'retry_waiting',
            'A `remote_read_replay_safe` job that lost a serialization race '
            'must remain safely retryable.',
        )
        self.assertEqual(error_class, 'concurrency_race_conflict')

    # ------------------------------------------------------------------
    # Scenario 1 -- both verdicts verified, the store converges to complete
    # ------------------------------------------------------------------

    def test_the_conflicting_settlement_converges_to_complete(self):
        fixture = self._commit_fixture()
        trace = self._drain_once(fixture, {})

        mid = self._observe(fixture)
        self._assert_genuine_conflict(trace, mid, fixture['job_a_id'])
        self.assertEqual(
            mid['state'], 'in_progress',
            'Neither transaction settled: B was not last, and A aborted. '
            'This is precisely the moment the old implementation stopped '
            'at -- with no job left to notice.',
        )
        self.assertEqual(
            mid['bindings'][fixture['binding_b_id']], 'verified',
            'B\'s verdict committed and survived A\'s rollback.',
        )
        self.assertEqual(
            mid['bindings'][fixture['binding_a_id']], 'pending',
            'A\'s verdict was rolled back with its aborted transaction.',
        )

        # The real dispatcher re-drives the job on a fresh snapshot.
        self._make_retry_due(fixture)
        self._drain_once(fixture, {'sibling_ran': True}, run_sibling=False)

        final = self._observe(fixture)
        self.assertEqual(
            final['state'], 'complete',
            'The re-driven job sees the sibling verdict its aborted '
            'predecessor could not, and settles.',
        )
        self.assertEqual(final['generation'], fixture['generation'])
        self.assertEqual(
            set(final['bindings'].values()), {'verified'},
        )
        self.assertGreaterEqual(
            final['settle_seq'], 2,
            'Every settle attempt writes the serialization row, including '
            'the one that declined and the one that aborted.',
        )
        self.assertEqual(
            final['jobs'][fixture['job_a_id']][0], 'succeeded',
        )

    # ------------------------------------------------------------------
    # Scenario 2 -- one review verdict, the store converges to review_required
    # ------------------------------------------------------------------

    def test_the_conflicting_settlement_converges_to_review_required(self):
        fixture = self._commit_fixture()
        # B's product is gone from Shopify, so B's verdict is `review`.
        trace = self._drain_once(fixture, {}, missing_gid=fixture['gid_b'])

        mid = self._observe(fixture)
        self._assert_genuine_conflict(trace, mid, fixture['job_a_id'])
        self.assertEqual(mid['state'], 'in_progress')
        self.assertEqual(
            mid['bindings'][fixture['binding_b_id']], 'review',
        )

        self._make_retry_due(fixture)
        self._drain_once(
            fixture, {'sibling_ran': True}, missing_gid=fixture['gid_b'],
            run_sibling=False,
        )

        final = self._observe(fixture)
        self.assertEqual(
            final['state'], 'review_required',
            'A review verdict from the transaction that WON the race must '
            'survive the loser\'s rollback and bind the settled outcome.',
        )
        self.assertEqual(final['generation'], fixture['generation'])
        self.assertEqual(
            final['bindings'][fixture['binding_a_id']], 'verified',
        )
        self.assertEqual(
            final['bindings'][fixture['binding_b_id']], 'review',
        )

        # And the block is still on, which is the operator-visible half.
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            with self.assertRaises(UserError) as caught:
                store._assert_export_reconciliation_complete()
            self.assertIn(
                'missing, archived or materially different',
                str(caught.exception),
            )
            cr.rollback()
        finally:
            cr.close()

    # ------------------------------------------------------------------
    # Sensitivity -- remove the boundary, get the defect back
    # ------------------------------------------------------------------

    def test_without_the_serialization_boundary_the_store_is_stranded(self):
        """The proof that the boundary is load-bearing.

        Identical fixture, identical interleaving, identical everything --
        except `_serialize_reconcile_settlement` is a no-op. With no
        conflicting write there is no conflict, so worker A reads its
        siblings from its own snapshot, cannot see B's committed verdict,
        declines exactly as B did, and commits.

        The result is the original TD-015 defect, on demand: every binding
        terminal, both jobs `succeeded`, the store permanently
        `in_progress`, and no job left that could ever settle it.
        """
        fixture = self._commit_fixture()
        trace = self._drain_once(fixture, {}, bypass=True)

        self.assertNotEqual(trace['drain_pid'], trace['sibling_pid'])
        self.assertEqual(
            [
                message for message in trace['log']
                if 'PostgreSQL concurrency failure' in message
            ], [],
            'With the boundary removed there must be NO conflict -- that is '
            'the whole point, and it is why the store strands.',
        )

        stranded = self._observe(fixture)
        self.assertEqual(
            set(stranded['bindings'].values()), {'verified'},
            'Every binding reached a terminal verdict.',
        )
        self.assertEqual(
            {state for state, _error in stranded['jobs'].values()},
            {'succeeded'},
            'Both jobs finished successfully and neither is coming back.',
        )
        self.assertEqual(
            stranded['state'], 'in_progress',
            'THE DEFECT: every binding is terminal and the store is still '
            'blocked, with no job left to notice. If this assertion ever '
            'fails, the regression above has stopped proving anything.',
        )
        self.assertEqual(
            stranded['settle_seq'], 0,
            'The bypass really did remove the serialization write.',
        )

        # And the production implementation is back in place afterwards --
        # the bypass is a context manager, and this is what proves it exited.
        Store = self.env['shopify.connector.store']
        self.assertEqual(
            type(Store)._serialize_reconcile_settlement.__name__,
            '_serialize_reconcile_settlement',
            'The sensitivity lever must never outlive the test that pulled '
            'it.',
        )

    # ------------------------------------------------------------------
    # The production fact that shapes the interleaving above
    # ------------------------------------------------------------------

    def test_a_second_worker_cannot_claim_past_a_locked_job(self):
        """Why worker B drives the handler rather than a second drain.

        `_drain_one` claims with `_claim_for_dispatch(1)`: search
        `order='id asc', limit=1`, then `try_lock_for_update()`, which is
        `FOR UPDATE SKIP LOCKED` at the pinned Odoo 19 commit. A concurrent
        worker whose single candidate is already locked therefore locks
        nothing and dispatches nothing -- it does not leapfrog to the next
        job.

        Asserted here rather than asserted in prose, because the shape of
        the race proof above depends on it being true.
        """
        fixture = self._commit_fixture()
        holder = self._open_bounded()
        try:
            henv = api.Environment(holder, SUPERUSER_ID, {})
            locked = henv['shopify.connector.job'].browse(
                fixture['job_a_id'],
            ).try_lock_for_update()
            self.assertTrue(locked, 'worker A must hold the lower-id job')

            other = self._open_bounded()
            try:
                oenv = api.Environment(other, SUPERUSER_ID, {})
                claimed = oenv['shopify.connector.job']._claim_for_dispatch(1)
                self.assertFalse(
                    claimed,
                    'A second worker claimed %r while the lowest-id '
                    'candidate was locked; the interleaving in this class '
                    'is built on it claiming nothing.' % claimed,
                )
                other.rollback()
            finally:
                other.close()
            holder.rollback()
        finally:
            holder.close()
