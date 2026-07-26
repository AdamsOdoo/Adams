"""Media export is append-only, READY-gated and duplicate-safe."""

import base64
import hashlib

from odoo.tests.common import tagged

from ..models.shopify_connector_media_export_service import (
    JOB_TYPE_MEDIA_ASSOCIATE,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_POLL,
    JOB_TYPE_MEDIA_STAGE,
    JOB_TYPE_MEDIA_UPLOAD,
    image_checksum,
)
from ..models.shopify_connector_product_export_service import (
    ExportPreC2FailClosedError,
)
from .common import ExportCase, FakeSendResponse, FILE_GID, PRODUCT_GID

# A 1x1 PNG. Small, real, and decodable — a fake byte string would not survive
# `base64.b64decode` in the service.
PNG_1X1 = base64.b64encode(base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8'
    b'AAAwAB/AL+gN0AAAAASUVORK5CYII='
))


@tagged('post_install', '-at_install')
class TestMediaExportPipeline(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template()
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        self.template.write({'image_1920': PNG_1X1})
        self.checksum = image_checksum(base64.b64decode(PNG_1X1))

    def _media_row(self, remote_status='staged', **extra):
        values = {
            'store_id': self.store.id,
            'product_template_binding_id': self.binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': self.checksum,
            'connector_filename': self.Media._connector_filename(
                self.template.id, self.checksum,
            ),
            'shopify_gid': 'pending:seed-%s' % self.checksum[:8],
            'remote_status': remote_status,
        }
        values.update(extra)
        return self.MediaBinding.sudo().create(values)

    def _applying_preview(self):
        preview = self.make_preview(
            export_path='update', binding=self.binding, state='applying',
            steps=[{'step': JOB_TYPE_MEDIA_STAGE, 'state': 'pending',
                    'role': 'primary', 'checksum': self.checksum,
                    'odoo_variant_id': False}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        return preview

    # ------------------------------------------------------------------
    # The READY gate
    # ------------------------------------------------------------------

    def test_association_is_refused_before_ready(self):
        preview = self._applying_preview()
        for index, status in enumerate(('staged', 'uploaded', 'processing')):
            with self.subTest(status=status):
                # A distinct checksum per row: the registry's uniqueness index
                # on (store, template binding, role, checksum) is real, and
                # three rows for one image would rightly violate it.
                row = self._media_row(
                    remote_status=status, shopify_gid=FILE_GID + status,
                    odoo_image_checksum='%064d' % index,
                )
                job = self.make_job(
                    JOB_TYPE_MEDIA_ASSOCIATE, row._name, row.id, PRODUCT_GID,
                )
                snapshot = self.Media._prepare_local_media_associate(job)
                with self.assertRaises(ExportPreC2FailClosedError) as catcher:
                    self.Media._prepare_preconditions_media_associate(
                        snapshot, {},
                    )
                self.assertIn('READY', catcher.exception.message)

    def test_association_is_built_only_with_references_to_add(self):
        preview = self._applying_preview()
        row = self._media_row(remote_status='ready', shopify_gid=FILE_GID)
        job = self.make_job(
            JOB_TYPE_MEDIA_ASSOCIATE, row._name, row.id, PRODUCT_GID,
        )
        snapshot = self.Media._prepare_local_media_associate(job)
        request = self.Media._prepare_preconditions_media_associate(
            snapshot, {},
        )
        entry = request['variables']['files'][0]
        self.assertEqual(entry['id'], FILE_GID)
        self.assertEqual(entry['referencesToAdd'], [PRODUCT_GID])
        # A detach is a removal, and this pipeline is append-only.
        self.assertNotIn('referencesToRemove', entry)
        self.assertIn('fileUpdate', request['operation'])

    def test_a_file_gid_placeholder_can_never_be_associated(self):
        preview = self._applying_preview()
        row = self._media_row(remote_status='ready')
        job = self.make_job(
            JOB_TYPE_MEDIA_ASSOCIATE, row._name, row.id, PRODUCT_GID,
        )
        snapshot = self.Media._prepare_local_media_associate(job)
        with self.assertRaises(ExportPreC2FailClosedError):
            self.Media._prepare_preconditions_media_associate(snapshot, {})

    # ------------------------------------------------------------------
    # The poll drives the gate, and FAILED never associates
    # ------------------------------------------------------------------

    def test_poll_promotes_to_ready_and_enqueues_the_association(self):
        self._applying_preview()
        row = self._media_row(remote_status='uploaded', shopify_gid=FILE_GID)
        job = self.make_job(JOB_TYPE_MEDIA_POLL, row._name, row.id)
        job.sudo().write({'state': 'running'})
        body = {'data': {
            'node': {'id': FILE_GID, 'fileStatus': 'READY', 'fileErrors': []},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Media._handle_product_export_media_poll(job)
        row.invalidate_recordset()
        self.assertEqual(row.remote_status, 'ready')
        self.assertTrue(self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_MEDIA_ASSOCIATE),
        ]))

    def test_poll_keeps_withholding_while_processing(self):
        self._applying_preview()
        row = self._media_row(remote_status='uploaded', shopify_gid=FILE_GID)
        job = self.make_job(JOB_TYPE_MEDIA_POLL, row._name, row.id)
        job.sudo().write({'state': 'running'})
        body = {'data': {
            'node': {'id': FILE_GID, 'fileStatus': 'PROCESSING',
                     'fileErrors': []},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Media._handle_product_export_media_poll(job)
        row.invalidate_recordset()
        self.assertEqual(row.remote_status, 'processing')
        self.assertFalse(self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_MEDIA_ASSOCIATE),
        ]))

    def test_poll_fails_closed_on_a_failed_file(self):
        self._applying_preview()
        row = self._media_row(remote_status='uploaded', shopify_gid=FILE_GID)
        job = self.make_job(JOB_TYPE_MEDIA_POLL, row._name, row.id)
        job.sudo().write({'state': 'running'})
        body = {'data': {
            'node': {'id': FILE_GID, 'fileStatus': 'FAILED',
                     'fileErrors': [{'code': 'INVALID_IMAGE_FILE_SIZE',
                                     'details': 'x', 'message': 'y'}]},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Media._handle_product_export_media_poll(job)
        row.invalidate_recordset()
        job.invalidate_recordset()
        self.assertEqual(row.remote_status, 'failed')
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(self.env['shopify.connector.job'].search_count([
            ('job_type', '=', JOB_TYPE_MEDIA_ASSOCIATE),
        ]))

    # ------------------------------------------------------------------
    # Duplicate safety by checksum
    # ------------------------------------------------------------------

    def test_an_unchanged_image_is_a_no_op(self):
        self._media_row(remote_status='associated', shopify_gid=FILE_GID)
        steps, diff = self.Media._preview_media(
            self.store, self.template, self.binding,
        )
        self.assertEqual(steps, [])
        self.assertFalse(diff['exported'])

    def test_a_changed_image_plans_an_append(self):
        steps, diff = self.Media._preview_media(
            self.store, self.template, self.binding,
        )
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['step'], JOB_TYPE_MEDIA_STAGE)
        self.assertTrue(diff['exported'])
        self.assertIn('APPENDED', diff['reason'])

    def test_the_filename_is_deterministic_from_template_and_checksum(self):
        first = self.Media._connector_filename(self.template.id, self.checksum)
        second = self.Media._connector_filename(self.template.id, self.checksum)
        self.assertEqual(first, second)
        self.assertIn(self.checksum[:8], first)
        self.assertTrue(first.startswith('odoo-%s-' % self.template.id))

    def test_media_export_is_off_without_an_explicit_odoo_direction(self):
        for value in (False, 'shopify'):
            with self.subTest(direction=value):
                self.settings.sudo().write({'media_source_of_truth': value})
                steps, diff = self.Media._preview_media(
                    self.store, self.template, self.binding,
                )
                self.assertEqual(steps, [])
                self.assertFalse(diff['exported'])
                self.assertIn('media_source_of_truth', diff['reason'])

    def test_media_is_not_planned_before_the_product_exists(self):
        steps, diff = self.Media._preview_media(
            self.store, self.template, self.TemplateBinding.browse(),
        )
        self.assertEqual(steps, [])
        self.assertIn('once the product exists', diff['reason'])

    # ------------------------------------------------------------------
    # Supersession retains, never deletes
    # ------------------------------------------------------------------

    def test_a_superseded_row_is_flagged_and_its_file_retained(self):
        old = self._media_row(
            remote_status='associated', shopify_gid=FILE_GID + 'old',
            odoo_image_checksum='a' * 64,
        )
        new = self._media_row(
            remote_status='associated', shopify_gid=FILE_GID + 'new',
        )
        self.Media._flag_superseded_rows(new)
        old.invalidate_recordset()
        self.assertTrue(old.orphan_cleanup_candidate)
        self.assertFalse(new.orphan_cleanup_candidate)
        # The row still exists: it is the only proof of which remote File this
        # connector created.
        self.assertTrue(old.exists())

    def test_a_media_row_can_never_be_deleted(self):
        row = self._media_row()
        with self.assertRaises(Exception):
            row.sudo().unlink()

    # ------------------------------------------------------------------
    # The staged upload refuses a non-HTTPS target and a changed image
    # ------------------------------------------------------------------

    def test_upload_refuses_a_non_https_target(self):
        self._applying_preview()
        row = self._media_row(
            remote_status='staged',
            staged_upload_url='http://insecure.example/upload',
            staged_resource_url='https://cdn.example/resource',
        )
        job = self.make_job(JOB_TYPE_MEDIA_UPLOAD, row._name, row.id)
        job.sudo().write({'state': 'running'})
        with self.assertRaises(Exception) as catcher:
            self.Media._handle_product_export_media_upload(job)
        self.assertIn('HTTPS', str(catcher.exception))

    def test_upload_refuses_when_the_image_changed_after_preview(self):
        self._applying_preview()
        row = self._media_row(
            remote_status='staged',
            odoo_image_checksum='b' * 64,
            staged_upload_url='https://upload.example/target',
            staged_resource_url='https://cdn.example/resource',
        )
        job = self.make_job(JOB_TYPE_MEDIA_UPLOAD, row._name, row.id)
        job.sudo().write({'state': 'running'})
        with self.assertRaises(Exception) as catcher:
            self.Media._handle_product_export_media_upload(job)
        self.assertIn('changed', str(catcher.exception))

    # ------------------------------------------------------------------
    # Verification read adopts instead of re-uploading
    # ------------------------------------------------------------------

    def test_file_create_reconciliation_adopts_a_single_match(self):
        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain
            preconditions_snapshot = {
                'filename': self.Media._connector_filename(
                    self.template.id, self.checksum,
                ),
            }

        body = {'data': {
            'files': {'nodes': [{'id': FILE_GID, 'fileStatus': 'READY'}]},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            verdict = self.Media._reconcile_media_file_create(_Attempt())
        self.assertEqual(verdict['verdict'], 'applied')
        self.assertEqual(verdict['evidence']['file']['id'], FILE_GID)

    def test_file_create_reconciliation_refuses_two_matches(self):
        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain
            preconditions_snapshot = {'filename': 'odoo-1-abc.png'}

        body = {'data': {
            'files': {'nodes': [
                {'id': FILE_GID + 'a', 'fileStatus': 'READY'},
                {'id': FILE_GID + 'b', 'fileStatus': 'READY'},
            ]},
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            verdict = self.Media._reconcile_media_file_create(_Attempt())
        self.assertEqual(verdict['action'], 'block_manual_review')
        self.assertEqual(verdict['error_class'], 'shopify_user_errors_validation')

    def test_staging_reconciliation_never_assumes_the_target_is_usable(self):
        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain

        body = {'data': {
            'shop': {'myshopifyDomain': self.store.shop_domain},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            verdict = self.Media._reconcile_media_stage(_Attempt())
        self.assertEqual(verdict['verdict'], 'not_applied')
        self.assertEqual(verdict['action'], 'block_manual_review')
        # The identity is OBSERVED, not echoed back from the attempt.
        self.assertEqual(
            verdict['observed_store_identity'], self.store.shop_domain,
        )

    def test_staging_reconciliation_refuses_a_different_store(self):
        class _Attempt:
            store_id = self.store
            expected_store_identity = self.store.shop_domain

        body = {'data': {
            'shop': {'myshopifyDomain': 'someone-else.myshopify.com'},
        }}
        response = FakeSendResponse(body)
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            verdict = self.Media._reconcile_media_stage(_Attempt())
        self.assertEqual(verdict['error_class'], 'store_identity_mismatch')

    def test_a_failed_media_link_blocks_the_plan_entry_it_belongs_to(self):
        """The plan holds one entry per image; every link resolves that one.

        Keying the advance on the calling job's own type would look right and
        do nothing, because `media_upload`/`media_file_create`/
        `media_associate` are not in the plan -- leaving a failed image's
        entry pending forever.
        """
        preview = self._applying_preview()
        row = self._media_row(remote_status='uploaded', shopify_gid=FILE_GID)
        self.Media._advance_media(
            row, JOB_TYPE_MEDIA_ASSOCIATE, None, completed=False,
        )
        self.env.flush_all()
        preview.invalidate_recordset()
        states = [
            step['state']
            for step in (preview.apply_plan or {}).get('steps') or []
        ]
        self.assertEqual(states, ['blocked'])
