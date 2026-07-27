"""TD-013: a stale confirmation may never authorise a Shopify mutation.

The defect these tests close
----------------------------
`_handle_product_export_apply` checked `preview._is_expired()` once, before
it built the plan, and nothing re-checked it afterwards. A plan is a *chain*
of separate jobs — create, then variants, then identity, then five media
jobs — each in its own transaction, each potentially minutes or hours apart
when the queue is busy or a step retries. The pre-C2 assertion that runs in
front of each of those jobs verified the preview's *state* and the
*identity* of the confirming user, and never once looked at `expires_at` or
at whether the operator had edited the product since.

So the guard was: check the milk's date once when you open the fridge, then
drink from it all week.

There are two boundaries here and they need opposite behaviour, which is
why there are two guards and two groups of tests:

**Pre-transport** (`_assert_preview_unexpired_pre_c2`) — nothing has been
sent, so refusing is free and correct. It raises the repository's
"nothing was transported" signal, `ExportPreC2FailClosedError`, which
`_recover_pre_c2_failure` turns into a blocked job carrying the message.

**Post-transport** (`_advance_plan`) — the step that just finished *did*
reach Shopify. Expiry proves nothing about it and must not be allowed to
retroactively deny it. What expiry forbids is spending the stale
confirmation on the *next* mutation, so the chain stops with its remaining
steps marked `blocked` and everything already applied left intact.

Both expiry directions are covered, because `_is_expired` has two:
`expires_at` passing, and the Odoo source being edited after the operator
reviewed the diff. The second is the one an operator actually hits.
"""

from odoo import fields
from odoo.tests.common import tagged

from ..models.shopify_connector_media_export_service import (
    JOB_TYPE_MEDIA_ASSOCIATE,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_STAGE,
    image_checksum,
)
from ..models.shopify_connector_product_export_service import (
    ExportPreC2FailClosedError,
    JOB_TYPE_BINDING_NAMESPACE,
    JOB_TYPE_CREATE,
    JOB_TYPE_UPDATE,
    JOB_TYPE_VARIANTS_CREATE,
    JOB_TYPE_VARIANTS_UPDATE,
)
from .common import ExportCase, FILE_GID, PRODUCT_GID, VARIANT_GID
from .test_media_export_pipeline import PNG_1X1

import base64


@tagged('post_install', '-at_install')
class TestExportMutationExpiry(ExportCase):
    """Every mutation family refuses to build a request on a stale preview."""

    def setUp(self):
        super().setUp()
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        # One binding, reused. `(store_id, shopify_gid)` is unique, so a
        # per-subtest `bind_template()` would collide rather than test
        # anything.
        self.binding = self.bind_template()

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _confirmed_applying(self, export_path='update', binding=None,
                            steps=None, diff=None, stale=False,
                            source_edited=False):
        """A confirmed, in-flight preview.

        Two ways to make it stale, matching `_is_expired`'s two arms:

        `stale=True` — born past its deadline. Expiry cannot be moved after
        creation (`expires_at` is deliberately absent from
        `WRITE_SURFACES`), which is a property worth keeping, so the
        fixture sets the deadline at birth rather than reaching around the
        guard.

        `source_edited=True` — records a `source_write_date` from before
        the product's current one, i.e. exactly the state a preview is left
        in when the operator edits the product afterwards. It cannot be
        produced by writing to the template mid-test, because Odoo stamps
        `write_date` from the cursor-cached transaction timestamp; see the
        note in `common.make_preview`.
        """
        preview = self.make_preview(
            export_path=export_path, binding=binding, state='applying',
            steps=steps or [], diff=diff,
            expires_at=(
                fields.Datetime.subtract(fields.Datetime.now(), hours=1)
                if stale else None
            ),
            source_write_date=(
                fields.Datetime.subtract(
                    self.Preview._source_write_date(self.template), hours=1,
                ) if source_edited else None
            ),
        )
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': self.env.uid,
            'confirmed_at': preview.previewed_at,
        })
        return preview

    def _assert_refused(self, callable_, *args):
        with self.assertRaises(ExportPreC2FailClosedError) as caught:
            callable_(*args)
        self.assertEqual(
            caught.exception.error_class, 'destructive_write_guard_blocked',
            'An expired confirmation is a destructive-write block, because '
            'the guard is what stands between a stale diff and a merchant '
            'store.',
        )
        self.assertIn(
            'no longer valid', caught.exception.message,
            'The operator-facing reason must name expiry, not merely fail.',
        )
        return caught.exception

    # ------------------------------------------------------------------
    # The five product mutation families
    # ------------------------------------------------------------------

    def _product_family_cases(self):
        """(job_type, preconditions method, preview kwargs) per family."""
        return (
            (
                JOB_TYPE_CREATE,
                self.Service._prepare_preconditions_create,
                {'export_path': 'create', 'binding': None,
                 'steps': [{'step': JOB_TYPE_CREATE, 'state': 'pending'}]},
                False,
            ),
            (
                JOB_TYPE_UPDATE,
                self.Service._prepare_preconditions_update,
                {'export_path': 'update',
                 'steps': [{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                            'fields': ['title']}]},
                True,
            ),
            (
                JOB_TYPE_VARIANTS_UPDATE,
                self.Service._prepare_preconditions_variants_update,
                {'export_path': 'update',
                 'steps': [{'step': JOB_TYPE_VARIANTS_UPDATE,
                            'state': 'pending',
                            'variant_gids': [VARIANT_GID]}]},
                True,
            ),
            (
                JOB_TYPE_VARIANTS_CREATE,
                self.Service._prepare_preconditions_variants_create,
                {'export_path': 'update',
                 'steps': [{'step': JOB_TYPE_VARIANTS_CREATE,
                            'state': 'pending',
                            'odoo_variant_ids': []}]},
                True,
            ),
            (
                JOB_TYPE_BINDING_NAMESPACE,
                self.Service._prepare_preconditions_binding_namespace,
                {'export_path': 'update',
                 'steps': [{'step': JOB_TYPE_BINDING_NAMESPACE,
                            'state': 'pending'}]},
                True,
            ),
        )

    def test_every_product_mutation_family_refuses_a_clock_expired_preview(self):
        for job_type, method, kwargs, needs_binding in (
            self._product_family_cases()
        ):
            with self.subTest(family=job_type):
                kwargs = dict(kwargs)
                if needs_binding:
                    kwargs['binding'] = self.binding
                preview = self._confirmed_applying(stale=True, **kwargs)
                job = self.make_job(
                    job_type, preview._name, preview.id,
                    preview.remote_product_gid or False,
                )
                snapshot = self.Service._prepare_local_common(job)
                self._assert_refused(method, snapshot, {})

    def test_every_product_mutation_family_refuses_an_edited_source(self):
        """The window is still open; the product changed underneath it."""
        for job_type, method, kwargs, needs_binding in (
            self._product_family_cases()
        ):
            with self.subTest(family=job_type):
                kwargs = dict(kwargs)
                if needs_binding:
                    kwargs['binding'] = self.binding
                preview = self._confirmed_applying(
                    source_edited=True, **kwargs
                )
                self.assertGreater(
                    preview.expires_at, fields.Datetime.now(),
                    'This case must exercise the SOURCE-EDIT direction, so '
                    'the validity window has to still be open.',
                )
                job = self.make_job(
                    job_type, preview._name, preview.id,
                    preview.remote_product_gid or False,
                )
                snapshot = self.Service._prepare_local_common(job)
                self._assert_refused(method, snapshot, {})

    # ------------------------------------------------------------------
    # The three media mutation families
    #
    # These resolve their preview by ROW, not by job, so they never passed
    # through `_assert_confirmed_preview_pre_c2` and had no expiry check of
    # any kind before TD-013.
    # ------------------------------------------------------------------

    def _media_fixtures(self, remote_status, stale=False,
                        source_edited=False, **extra):
        binding = self.binding
        self.template.write({'image_1920': PNG_1X1})
        checksum = image_checksum(base64.b64decode(PNG_1X1))
        values = {
            'store_id': self.store.id,
            'product_template_binding_id': binding.id,
            'media_role': 'primary',
            'odoo_image_checksum': checksum,
            'connector_filename': self.Media._connector_filename(
                self.template.id, checksum,
            ),
            'shopify_gid': 'pending:seed-%s' % checksum[:8],
            'remote_status': remote_status,
        }
        values.update(extra)
        row = self.MediaBinding.sudo().create(values)
        preview = self._confirmed_applying(
            binding=binding, stale=stale, source_edited=source_edited,
            steps=[{'step': JOB_TYPE_MEDIA_STAGE, 'state': 'pending',
                    'role': 'primary', 'checksum': checksum,
                    'odoo_variant_id': False}],
        )
        return binding, row, preview

    def test_media_stage_refuses_an_expired_preview(self):
        _binding, row, _preview = self._media_fixtures(
            'staged', stale=True,
        )
        job = self.make_job(JOB_TYPE_MEDIA_STAGE, row._name, row.id)
        snapshot = self.Media._prepare_local_media_stage(job)
        self._assert_refused(
            self.Media._prepare_preconditions_media_stage, snapshot, {},
        )

    def test_media_file_create_refuses_an_expired_preview(self):
        _binding, row, _preview = self._media_fixtures(
            'uploaded', stale=True,
            staged_resource_url='https://example.invalid/staged',
        )
        job = self.make_job(JOB_TYPE_MEDIA_FILE_CREATE, row._name, row.id)
        snapshot = self.Media._prepare_local_media_file_create(job)
        self._assert_refused(
            self.Media._prepare_preconditions_media_file_create, snapshot, {},
        )

    def test_media_associate_refuses_an_expired_preview(self):
        """The last and most consequential media mutation.

        `fileUpdate(referencesToAdd:)` is the call that puts an image on a
        merchant's product page. Reaching it on a confirmation the operator
        gave for a different image is precisely the outcome TD-013 exists
        to prevent.
        """
        _binding, row, _preview = self._media_fixtures(
            'ready', source_edited=True, shopify_gid=FILE_GID,
        )
        job = self.make_job(
            JOB_TYPE_MEDIA_ASSOCIATE, row._name, row.id, PRODUCT_GID,
        )
        snapshot = self.Media._prepare_local_media_associate(job)
        self._assert_refused(
            self.Media._prepare_preconditions_media_associate, snapshot, {},
        )

    def test_media_associate_still_builds_on_a_live_confirmation(self):
        """The guard must not break the working path it now stands in."""
        _binding, row, _preview = self._media_fixtures(
            'ready', shopify_gid=FILE_GID,
        )
        job = self.make_job(
            JOB_TYPE_MEDIA_ASSOCIATE, row._name, row.id, PRODUCT_GID,
        )
        snapshot = self.Media._prepare_local_media_associate(job)
        request = self.Media._prepare_preconditions_media_associate(
            snapshot, {},
        )
        self.assertEqual(
            request['variables']['files'][0]['referencesToAdd'],
            [PRODUCT_GID],
        )

    # ------------------------------------------------------------------
    # Admission-time validity, transport-time expiry
    # ------------------------------------------------------------------

    def test_valid_at_admission_expired_immediately_before_transport(self):
        """The exact race the single up-front check could not see.

        The apply orchestrator's check passes. The job is admitted. Then
        time moves — or the operator edits the product — and the request is
        built. Before TD-013 this produced a live Shopify mutation carrying
        a diff nobody had approved.
        """
        preview = self._confirmed_applying(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        job = self.make_job(
            JOB_TYPE_UPDATE, preview._name, preview.id, PRODUCT_GID,
        )
        snapshot = self.Service._prepare_local_common(job)

        # Admission-time: the guard is satisfied and the request builds.
        request = self.Service._prepare_preconditions_update(snapshot, {})
        self.assertIn('productUpdate', request['operation'])

        # ...then the confirmation goes stale before the mutation is sent,
        # WITHOUT the snapshot changing. `expires_at` cannot move after
        # creation and `write_date` cannot advance inside one transaction,
        # so the aging is applied to the preview's own recorded
        # `source_write_date` through its create surface -- the same state
        # an operator's edit leaves behind. The point of the test is that
        # the IDENTICAL snapshot, accepted a moment ago, is now refused.
        self.env.cr.execute(
            'UPDATE shopify_connector_product_export_preview '
            'SET source_write_date = source_write_date - interval %s '
            'WHERE id = %s', ('1 hour', preview.id),
        )
        preview.invalidate_recordset()
        self._assert_refused(
            self.Service._prepare_preconditions_update, snapshot, {},
        )

    def test_a_live_confirmation_is_never_refused(self):
        """No false positive: nothing about the apply chain expires itself.

        The apply consequences write to the BINDING and the PREVIEW, never
        to `product.template` or `product.product`. If a future change made
        a consequence touch the source, `_is_expired`'s source-write-date
        arm would start firing mid-chain and every multi-step export would
        block on its second step. This test is the alarm for that.
        """
        preview = self._confirmed_applying(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']},
                   {'step': JOB_TYPE_VARIANTS_UPDATE, 'state': 'pending',
                    'variant_gids': [VARIANT_GID]}],
        )
        for job_type, method in (
            (JOB_TYPE_UPDATE, self.Service._prepare_preconditions_update),
            (JOB_TYPE_VARIANTS_UPDATE,
             self.Service._prepare_preconditions_variants_update),
        ):
            with self.subTest(family=job_type):
                job = self.make_job(
                    job_type, preview._name, preview.id, PRODUCT_GID,
                )
                snapshot = self.Service._prepare_local_common(job)
                request = method(snapshot, {})
                self.assertTrue(request['operation'])

    # ------------------------------------------------------------------
    # The post-transport boundary: `_advance_plan`
    # ------------------------------------------------------------------

    def test_expiry_mid_plan_blocks_the_next_step_and_keeps_the_applied_one(self):
        preview = self._confirmed_applying(
            binding=self.binding,
            stale=True,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']},
                   {'step': JOB_TYPE_VARIANTS_UPDATE, 'state': 'pending',
                    'variant_gids': [VARIANT_GID]}],
        )
        advanced = self.Service._advance_plan(preview, JOB_TYPE_UPDATE)
        self.assertFalse(
            advanced,
            'A plan that stops on expiry has not advanced to its next step.',
        )
        preview.invalidate_recordset()
        states = {
            step['step']: step['state']
            for step in preview.apply_plan['steps']
        }
        self.assertEqual(
            states[JOB_TYPE_UPDATE], 'done',
            'The step that already reached Shopify keeps its outcome. '
            'Expiry is not evidence that a completed mutation did not '
            'happen.',
        )
        self.assertEqual(
            states[JOB_TYPE_VARIANTS_UPDATE], 'blocked',
            'The next mutation must be refused, not silently dropped and '
            'not marked done.',
        )
        self.assertEqual(preview.state, 'expired')
        self.assertNotEqual(
            preview.state, 'applied',
            'A part-applied export must never be recorded as applied.',
        )

    def test_expiry_mid_plan_enqueues_no_child_job(self):
        """The concrete consequence: no successor job is created."""
        preview = self._confirmed_applying(
            binding=self.binding,
            stale=True,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']},
                   {'step': JOB_TYPE_VARIANTS_UPDATE, 'state': 'pending',
                    'variant_gids': [VARIANT_GID]}],
        )
        Job = self.env['shopify.connector.job']
        domain = [('store_id', '=', self.store.id),
                  ('job_type', '=', JOB_TYPE_VARIANTS_UPDATE)]
        before = Job.sudo().search_count(domain)
        self.Service._advance_plan(preview, JOB_TYPE_UPDATE)
        self.assertEqual(
            Job.sudo().search_count(domain), before,
            'An expired preview must not enqueue the next mutation-bearing '
            'child.',
        )

    def test_an_unexpired_plan_still_advances_normally(self):
        preview = self._confirmed_applying(
            binding=self.binding,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']},
                   {'step': JOB_TYPE_VARIANTS_UPDATE, 'state': 'pending',
                    'variant_gids': [VARIANT_GID]}],
        )
        Job = self.env['shopify.connector.job']
        domain = [('store_id', '=', self.store.id),
                  ('job_type', '=', JOB_TYPE_VARIANTS_UPDATE)]
        before = Job.sudo().search_count(domain)
        self.assertTrue(self.Service._advance_plan(preview, JOB_TYPE_UPDATE))
        self.assertEqual(
            Job.sudo().search_count(domain), before + 1,
            'The guard must not break the ordinary multi-step chain.',
        )
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'applying')

    def test_the_final_step_of_an_expired_plan_still_records_applied(self):
        """Expiry gates the NEXT mutation; it does not un-apply the last one.

        When the step that just succeeded was the last one there is no next
        mutation to refuse, so the export is complete and must be recorded
        as such even though the window has since closed. Marking it expired
        here would lose the fact that Shopify was actually updated.
        """
        preview = self._confirmed_applying(
            binding=self.binding,
            stale=True,
            steps=[{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                    'fields': ['title']}],
        )
        self.assertTrue(self.Service._advance_plan(preview, JOB_TYPE_UPDATE))
        preview.invalidate_recordset()
        self.assertEqual(preview.state, 'applied')

    # ------------------------------------------------------------------
    # Coverage guard
    # ------------------------------------------------------------------

    def test_every_mutation_family_is_bound_to_the_expiry_guard(self):
        """Structural: a new mutation family cannot skip TD-013 silently.

        Every `_prepare_preconditions_*` method is a mutation boundary. Each
        must reach the expiry guard, either directly or through
        `_assert_confirmed_preview_pre_c2`. Adding a family without one is
        the exact shape of the original defect, so it fails here rather
        than in production.
        """
        import inspect

        from ..models import shopify_connector_media_export_service as media
        from ..models import shopify_connector_product_export_service as svc

        bound = []
        unbound = []
        for module in (svc, media):
            for _name, klass in inspect.getmembers(module, inspect.isclass):
                if klass.__module__ != module.__name__:
                    continue
                for name, member in inspect.getmembers(klass):
                    if not name.startswith('_prepare_preconditions_'):
                        continue
                    source = inspect.getsource(member)
                    if (
                        '_assert_preview_unexpired_pre_c2' in source
                        or '_assert_confirmed_preview_pre_c2' in source
                    ):
                        bound.append(name)
                    else:
                        unbound.append(name)
        self.assertFalse(unbound, (
            'These mutation families build a Shopify request without '
            're-checking that the confirmation authorising it is still '
            'valid (TD-013): %s' % sorted(set(unbound))
        ))
        self.assertEqual(
            len(set(bound)), 8,
            'Expected the 8 known mutation families to be bound to the '
            'expiry guard; found %s. If a family was legitimately added or '
            'removed, update this count in the same commit.'
            % sorted(set(bound)),
        )
