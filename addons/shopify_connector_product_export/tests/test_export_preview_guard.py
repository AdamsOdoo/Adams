"""Preview -> confirm -> apply is the only path, and staleness closes it."""

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user, tagged

from ..models.shopify_connector_media_export_service import (
    JOB_TYPE_MEDIA_STAGE,
)
from ..models.shopify_connector_product_export_service import (
    JOB_TYPE_APPLY,
    JOB_TYPE_PREVIEW,
    JOB_TYPE_UPDATE,
    MAX_PRODUCT_OPTIONS,
)
from .common import ExportCase, FakeSendResponse, PRODUCT_GID

# A real 1x1 PNG. `_decoded_image` base64-decodes and checksums the actual
# bytes, so a placeholder string would be discarded before a media step could
# ever be planned and the test would pass for the wrong reason.
ONE_PIXEL_PNG = (
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDw'
    b'AEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


def _product_read_body(updated_at='2026-07-26T00:00:00Z', shop=None,
                       title='Exportable Widget'):
    return {'data': {
        'product': {
            'id': PRODUCT_GID,
            'handle': 'exportable-widget',
            'title': title,
            'descriptionHtml': '<p>A widget.</p>',
            'vendor': 'Adams',
            'productType': 'Widgets',
            'tags': ['alpha', 'beta'],
            'status': 'DRAFT',
            'updatedAt': updated_at,
            'options': [],
            'variants': {'nodes': []},
            'collections': {'nodes': []},
            'metafields': {'nodes': []},
            'media': {'nodes': []},
        },
        'shop': {'myshopifyDomain': shop or 'export-test.myshopify.com'},
    }}


@tagged('post_install', '-at_install')
class TestExportPreviewGuard(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template(variant_gid=None)
        # The default test user is `__system__`, which is in no connector
        # group. Confirmation tests therefore run as a real reviewer:
        # `AccessError` subclasses `UserError`, so asserting `UserError`
        # against the system user would pass on the PERMISSION check and never
        # reach the guard under test.
        self.reviewer = new_test_user(
            self.env, login='export-reviewer-guard',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_reviewer',
        )

    # ------------------------------------------------------------------
    # Confirmation is a permission, and a re-verified one
    # ------------------------------------------------------------------

    def test_only_reviewer_or_admin_may_confirm(self):
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        operator = new_test_user(
            self.env, login='export-operator',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_operator',
        )
        with self.assertRaises(AccessError):
            preview.with_user(operator).action_confirm_export_preview()
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'previewed')
        self.assertFalse(preview.confirmed_uid)

    def test_confirmation_records_the_actor_and_enqueues_apply(self):
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        reviewer = new_test_user(
            self.env, login='export-reviewer',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_reviewer',
        )
        job = preview.with_user(reviewer).action_confirm_export_preview()
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'confirmed')
        self.assertEqual(preview.confirmed_uid, reviewer)
        self.assertEqual(job.job_type, JOB_TYPE_APPLY)

    def test_a_preview_with_no_steps_cannot_be_confirmed(self):
        preview = self.make_preview(binding=self.binding, steps=[])
        with self.assertRaises(UserError) as catcher:
            preview.with_user(self.reviewer).action_confirm_export_preview()
        self.assertIn('nothing that can be exported', str(catcher.exception))

    def test_an_expired_preview_cannot_be_confirmed(self):
        """Refused AND recorded as expired, in one call.

        The refusal and the expiry write happen together, so this cannot use
        `assertRaises`: Odoo's `_assertRaises` wraps the call in a savepoint
        (odoo/odoo@19.0 `odoo/tests/common.py` L502-L520) and rolls it back
        when the expected exception is raised, which would roll back the very
        side effect under test. The call is therefore made directly and the
        exception caught by hand.
        """
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        self.env.cr.execute(
            'UPDATE shopify_connector_product_export_preview '
            'SET expires_at = %s WHERE id = %s',
            (fields.Datetime.subtract(fields.Datetime.now(), hours=1),
             preview.id),
        )
        preview.invalidate_recordset()
        self.assertTrue(preview._is_expired())

        raised = None
        try:
            preview.with_user(self.reviewer).action_confirm_export_preview()
        except UserError as exc:
            raised = exc
        self.assertIsNotNone(raised, 'a stale preview must not be confirmable')
        self.assertIn('no longer current', str(raised))
        self.env.flush_all()
        preview.invalidate_recordset()
        # A preview that stays confirmable after a refusal is a guard that only
        # works while somebody is watching.
        self.assertEqual(preview.state, 'expired')
        self.assertFalse(preview.confirmed_uid)

    def test_an_odoo_side_edit_expires_the_preview(self):
        """The symmetric staleness direction: Odoo changed since the preview."""
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        self.assertFalse(preview._is_expired())
        self.env.cr.execute(
            'UPDATE product_template SET write_date = %s WHERE id = %s',
            (fields.Datetime.add(fields.Datetime.now(), hours=1),
             self.template.id),
        )
        self.template.invalidate_recordset()
        self.assertTrue(preview._is_expired())

    def test_a_variant_edit_also_expires_the_preview(self):
        """A price or barcode edit lands on product.product, leaving the
        template's own write_date untouched while changing what is exported."""
        preview = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        self.env.cr.execute(
            'UPDATE product_product SET write_date = %s WHERE id = %s',
            (fields.Datetime.add(fields.Datetime.now(), hours=1),
             self.variant.id),
        )
        self.variant.invalidate_recordset()
        self.assertTrue(preview._is_expired())

    # ------------------------------------------------------------------
    # Apply refuses without a confirmed, current preview
    # ------------------------------------------------------------------

    def test_apply_refuses_an_unconfirmed_preview(self):
        preview = self.make_preview(
            binding=self.binding, state='previewed',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        job = self.make_job(
            JOB_TYPE_APPLY, preview._name, preview.id, PRODUCT_GID,
        )
        job.sudo().write({'state': 'running'})
        self.Service._handle_product_export_apply(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            job.manual_review_subreason, 'destructive_write_guard_blocked',
        )

    def test_apply_refuses_when_the_remote_changed_since_the_preview(self):
        preview = self.make_preview(
            binding=self.binding, state='confirmed',
            remote_updated_at='2026-07-26T00:00:00Z',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        job = self.make_job(
            JOB_TYPE_APPLY, preview._name, preview.id, PRODUCT_GID,
        )
        job.sudo().write({'state': 'running'})
        response = FakeSendResponse(
            _product_read_body(updated_at='2026-07-26T09:00:00Z')
        )
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Service._handle_product_export_apply(job)
        job.invalidate_recordset()
        preview.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(preview.state, 'expired')

    def test_apply_admits_and_enqueues_the_first_step_when_current(self):
        preview = self.make_preview(
            binding=self.binding, state='confirmed',
            remote_updated_at='2026-07-26T00:00:00Z',
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        job = self.make_job(
            JOB_TYPE_APPLY, preview._name, preview.id, PRODUCT_GID,
        )
        job.sudo().write({'state': 'running'})
        response = FakeSendResponse(_product_read_body())
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            self.Service._handle_product_export_apply(job)
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'applying')
        enqueued = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', JOB_TYPE_UPDATE),
        ])
        self.assertEqual(len(enqueued), 1)

    # ------------------------------------------------------------------
    # The preview record is evidence, not a scratchpad
    # ------------------------------------------------------------------

    def test_the_reviewed_content_of_a_preview_is_immutable(self):
        preview = self.make_preview(binding=self.binding)
        # No surface at all -> refused outright.
        with self.assertRaises(AccessError):
            preview.sudo().write({'state': 'confirmed'})
        # A sanctioned surface still cannot rewrite what was reviewed.
        with self.assertRaises(ValidationError):
            preview._preview_surface('_record_plan_progress').write(
                {'diff': {'scalars': []}}
            )
        with self.assertRaises(ValidationError):
            preview._preview_surface('_record_plan_progress').write(
                {'blocked_differences': {'items': []}}
            )

    def test_a_preview_can_never_be_deleted(self):
        preview = self.make_preview(binding=self.binding)
        with self.assertRaises(AccessError):
            preview.unlink()
        with self.assertRaises(AccessError):
            preview.sudo().unlink()

    # ------------------------------------------------------------------
    # The blocking hold is the LAST word on the plan
    # ------------------------------------------------------------------

    def _give_the_template_too_many_options(self):
        """One more attribute line than Shopify's documented option ceiling.

        Each line carries a single value, so the variant count stays at one
        and the only ceiling this trips is the option one.
        """
        Attribute = self.env['product.attribute']
        Value = self.env['product.attribute.value']
        Line = self.env['product.template.attribute.line']
        for index in range(MAX_PRODUCT_OPTIONS + 1):
            attribute = Attribute.create({
                'name': 'Hold Axis %d' % index, 'create_variant': 'always',
            })
            value = Value.create({
                'name': 'Only', 'attribute_id': attribute.id,
            })
            Line.create({
                'product_tmpl_id': self.template.id,
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, value.ids)],
            })
        self.template.invalidate_recordset()

    def test_a_blocking_hold_also_withholds_the_media_plan(self):
        """A refused product shape may not export "the safe half".

        The hold used to run BEFORE the media planner, so it emptied the
        product plan and the media planner then refilled it: a product whose
        option shape had already been refused came back `previewed` with an
        executable media step, and a reviewer could confirm it. The hold is
        now the last word on the plan, and this test is the thing that keeps
        it there -- it fails if the two are ever reordered again.
        """
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        self.template.sudo().write({'image_1920': ONE_PIXEL_PNG})
        self._give_the_template_too_many_options()

        job = self.make_job(
            JOB_TYPE_PREVIEW, 'product.template', self.template.id,
        )
        job.sudo().write({'state': 'running'})
        response = FakeSendResponse(_product_read_body(title='Renamed Remotely'))
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            preview = self.Service._handle_product_export_preview(job)
        preview.invalidate_recordset()

        kinds = {
            item['kind']
            for item in (preview.blocked_differences or {}).get('items') or []
        }
        self.assertIn('too_many_options', kinds)
        # Not "no media step" by accident -- no step of ANY kind survives.
        self.assertEqual((preview.apply_plan or {}).get('steps'), [])
        self.assertNotIn(
            JOB_TYPE_MEDIA_STAGE,
            [step.get('step')
             for step in (preview.apply_plan or {}).get('steps') or []],
        )
        # And the state says so, rather than looking confirmable.
        self.assertEqual(preview.state, 'blocked')
        # The media section must not still advertise appends it will not do.
        self.assertFalse((preview.diff or {}).get('media', {}).get('exported'))
        self.assertEqual(
            (preview.diff or {}).get('media', {}).get('appends'), [],
        )

    def test_a_held_preview_cannot_be_confirmed(self):
        """The end-to-end consequence, asserted through the real door."""
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        self.template.sudo().write({'image_1920': ONE_PIXEL_PNG})
        self._give_the_template_too_many_options()

        job = self.make_job(
            JOB_TYPE_PREVIEW, 'product.template', self.template.id,
        )
        job.sudo().write({'state': 'running'})
        response = FakeSendResponse(_product_read_body(title='Renamed Remotely'))
        with self.send_patch(
            lambda self, store, body, token=None, mutation_context=None,
            r=response: r
        ):
            preview = self.Service._handle_product_export_preview(job)
        preview.invalidate_recordset()

        with self.assertRaises(UserError) as catcher:
            preview.with_user(self.reviewer).action_confirm_export_preview()
        # `blocked` is refused by the state check, before the empty-plan one.
        self.assertIn('previewed, unconfirmed', str(catcher.exception))

    def test_a_fresh_preview_expires_the_previous_one(self):
        first = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        second = self.make_preview(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        # `make_preview` writes rows directly; the service's own
        # supersede path is what the preview handler uses, so drive that.
        for row in self.Preview.sudo().search([
            ('id', '=', first.id), ('state', 'in', ('previewed', 'confirmed')),
        ]):
            row._record_expiry('superseded_by_fresh_preview')
        first.invalidate_recordset()
        self.assertEqual(first.state, 'expired')
        self.assertEqual(second.state, 'previewed')
