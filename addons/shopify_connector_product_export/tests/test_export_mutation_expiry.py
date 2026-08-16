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

import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

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
from odoo.tools import mute_logger


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

    @mute_logger(
        'odoo.addons.shopify_connector_product_export.models.'
        'shopify_connector_product_export_service'
    )
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

    @mute_logger(
        'odoo.addons.shopify_connector_product_export.models.'
        'shopify_connector_product_export_service'
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


# Non-standard: this class needs a GENUINE pooled connection with real commit
# boundaries, because the Layer 2 mutation route it exercises commits between
# C1 and C2 by design (`_drain_mutation_one`) and refuses outright on a shared
# in-test cursor: "Layer 2 mutation dispatch requires an owned cursor with real
# commit boundaries". It is bounded (statement_timeout + lock_timeout), creates
# its own store, and cleans up after itself. The suite runner runs it by tag.
@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_export_mutation_route')
class TestExportMutationExpiryThroughTheDispatcher(TransactionCase):
    """TD-013 through the REAL dispatcher, not through its helpers.

    Why this class exists
    ---------------------
    The TD-013 regressions above call `_prepare_preconditions_*` and
    `_advance_plan` directly. That is legitimate unit coverage of the guard
    and it is NOT proof that the guard is bound into the route a real job
    takes. A guard can be present in a method no production dispatch ever
    reaches -- which is the exact failure mode TD-011 turned out to have,
    on the same PR.

    So this drives `run_drain()`: the production claim, the
    `_is_mutation_job_type` branch, `_drain_mutation_one`, `prepare_local`,
    `prepare_preconditions` (where the TD-013 assertion lives),
    `_recover_pre_c2_failure`, and the fail-closed disposition. The
    transport is patched at `_send` -- the single choke point -- and
    asserted to receive nothing.

    Zero Shopify contact: `_send` is replaced by a function that fails the
    test if it is ever called, so a regression that let the request through
    surfaces as a failure rather than as an outbound connection.
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000

    def _open_bounded(self):
        """A genuine pooled cursor with both transaction-local PG limits.

        Same shape as the core module's genuine-connection lifecycle tests:
        a real connection so `commit()` is real, and bounded so a lock this
        test cannot acquire fails fast instead of hanging the suite.
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

    def _fixtures(self, env, suffix, stale=True):
        """A store, an applying+confirmed preview, and one mutation job.

        The preview is valid at admission and stale at its mutation
        boundary, which is the scenario TD-013 is about: `expires_at` is
        absent from the preview's write surfaces on purpose, so the fixture
        sets the deadline at birth rather than reaching around the guard.
        """
        store = env['shopify.connector.store'].create({
            'name': 'TD-013 route store %s' % suffix,
            'shop_domain': 'td013-route-%s.myshopify.com' % suffix,
            'api_version': SHOPIFY_API_VERSION,
            'state': 'connected',
        })
        # A credential, because `execute_business` refuses a connected store
        # with no usable token BEFORE `_send` -- so without one, the
        # live-confirmation control below could never reach the transport and
        # would "prove" the guard for the wrong reason. Set before the job is
        # enqueued, so the job captures the store's settled
        # `connection_generation`.
        # Batch 1 correction (§9.1): minted through the credential service's
        # write surface, which is now the only route to a credential row.
        # Mechanical, test-only; the surface avoids `action_set_token`'s
        # lifecycle lock, which would demote this `connected` store.
        env['shopify.connector.store.credential']._credential_surface(
            '_mutate_token',
        ).create({
            'store_id': store.id,
            'access_token': 'shpat_DUMMYDUMMYDUMMY0000000000000000',
            'credential_epoch': 1,
        })
        store.write({'state': 'connected'})
        env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'product_export_domain_enabled': True,
            'price_source_of_truth': 'odoo_authoritative',
        })
        template = env['product.template'].create({
            'name': 'TD-013 route widget %s' % suffix,
            'shopify_export_enabled': True,
        })
        binding = env['shopify.connector.product.template.binding'].create({
            'store_id': store.id,
            'product_template_id': template.id,
            'shopify_gid': 'gid://shopify/Product/TD013ROUTE%s' % suffix,
        })
        now = fields.Datetime.now()
        # Through the CREATE surface, like production. The preview model
        # refuses a bare `create()`, and `expires_at` is deliberately absent
        # from `WRITE_SURFACES`, so a stale confirmation has to be BORN
        # stale rather than aged by reaching around the guard.
        Preview = env[
            'shopify.connector.product.export.preview'
        ]._preview_surface('_create_preview')
        preview = Preview.create({
            'store_id': store.id,
            'product_template_id': template.id,
            'product_template_binding_id': binding.id,
            'export_path': 'update',
            'state': 'applying',
            'diff': {'scalars': [], 'untouched': {}},
            'apply_plan': {
                'steps': [{'step': JOB_TYPE_UPDATE, 'state': 'pending',
                           'fields': ['title']}],
                'cursor': 0,
            },
            'blocked_differences': {'items': []},
            'has_blocked_differences': False,
            'remote_product_gid': binding.shopify_gid,
            'remote_updated_at': '2026-07-26T00:00:00Z',
            'previewed_at': now,
            'source_write_date': Preview._source_write_date(template),
            'expires_at': (
                fields.Datetime.subtract(now, hours=1) if stale
                else fields.Datetime.add(now, hours=1)
            ),
        })
        preview._preview_surface('_record_confirmation').write({
            'confirmed_uid': env.uid,
            'confirmed_at': now,
        })
        job = env['shopify.connector.job.enqueue'].enqueue(
            store, 'manual_sync', JOB_TYPE_UPDATE,
            payload_hash=uuid.uuid4().hex,
            res_model=preview._name, res_id=preview.id,
            shopify_target_gid=binding.shopify_gid,
        )
        return store, preview, job

    def _drain_once(self, stale=True):
        """Run the production drain for exactly one mutation job.

        Returns `(job_state, error_class, subreason, send_calls,
        child_job_count)` read back on a THIRD connection, so what is
        asserted is what actually committed rather than what a cache held.
        """
        suffix = uuid.uuid4().hex[:8]
        Client = type(self.env['shopify.connector.api.client'])
        sent = []

        def refuse_send(_self, _store, request, token=None,
                        mutation_context=None):
            sent.append(request)
            raise AssertionError(
                'The transport choke point was reached. A stale confirmation '
                'must never authorise a Shopify mutation.'
            )

        cr = self._open_bounded()
        job_id = store_id = None
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store, _preview, job = self._fixtures(env, suffix, stale=stale)
            job_id, store_id = job.id, store.id
            env.flush_all()
            cr.commit()
            with patch.object(Client, '_send', refuse_send):
                env['shopify.connector.job.dispatch'].run_drain(1)
            cr.commit()
        finally:
            try:
                cr.rollback()
            finally:
                cr.close()

        observer = self._open_bounded()
        try:
            oenv = api.Environment(observer, SUPERUSER_ID, {})
            job = oenv['shopify.connector.job'].browse(job_id)
            # "Mutation job" is whatever the dispatcher itself would route
            # down the Layer 2 path, read from the live registry rather than
            # from a list in this file that could drift from it.
            mutation_types = list(
                oenv['shopify.connector.job.dispatch']
                ._get_reconciliation_strategies()
            )
            children = oenv['shopify.connector.job'].search_count([
                ('store_id', '=', store_id),
                ('job_type', 'in', mutation_types),
                ('id', '!=', job_id),
            ])
            result = (
                job.state, job.error_class, job.manual_review_subreason,
                list(sent), children,
            )
        finally:
            try:
                observer.rollback()
            finally:
                observer.close()
        self._cleanup(store_id)
        return result

    def _cleanup(self, store_id):
        """Remove this test's committed rows on its own connection.

        Committed fixtures are not rolled back by `TransactionCase`, so they
        would otherwise leak into the rest of the run. Job logs are
        append-only and jobs cannot be unlinked through the ORM, so the
        teardown is raw SQL scoped to this one store id.

        The order is dictated by real foreign keys, and one of them points
        BOTH ways: a job names its mutation attempt (`mutation_attempt_id`)
        and an attempt names its job. The reference from the job side is
        nulled first, which is what breaks the cycle -- deleting either
        table first without that raises `ForeignKeyViolation`.
        """
        cr = self._open_bounded()
        try:
            cr.execute(
                'UPDATE shopify_connector_job SET mutation_attempt_id = NULL '
                'WHERE store_id = %s',
                (store_id,),
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
                # The table names are a fixed literal tuple in this file, so
                # the only interpolated value is the parameterised store id.
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

    # ------------------------------------------------------------------
    # The binding proof
    # ------------------------------------------------------------------

    def test_a_stale_confirmation_is_refused_by_the_real_mutation_route(self):
        """Requirements 1-6 of the TD-013 evidence correction, in one run."""
        state, error_class, subreason, sent, children = self._drain_once()

        self.assertEqual(
            sent, [],
            'Requirement 4: the transport choke point must receive zero '
            'calls. Anything here means a stale confirmation reached '
            'Shopify.',
        )
        self.assertEqual(
            state, 'blocked_manual_review',
            'Requirement 5: the accepted fail-closed disposition for a '
            'pre-C2 refusal is a job held for manual review.',
        )
        self.assertEqual(error_class, 'destructive_write_guard_blocked')
        self.assertEqual(subreason, 'destructive_write_guard_blocked')
        self.assertEqual(
            children, 0,
            'Requirement 6: a refused mutation must not admit the next step '
            'of the plan.',
        )

    def test_the_same_route_admits_a_live_confirmation(self):
        """The guard is sensitive to expiry, not to the route itself.

        Without this the test above would pass equally well if the route
        were broken for every mutation, which would prove nothing about
        TD-013. Here the confirmation is live, so the run gets PAST the
        expiry assertion and reaches the transport -- which this class
        still refuses, so the job fails rather than mutating. What matters
        is that `_send` WAS reached: the difference between the two tests
        is expiry and nothing else.
        """
        state, _error_class, _subreason, sent, _children = self._drain_once(
            stale=False,
        )
        self.assertTrue(
            sent,
            'A live confirmation must be allowed through to the transport, '
            'or the previous test proves only that the route is dead.',
        )
        self.assertNotEqual(state, 'succeeded')

    def test_the_guard_is_reached_from_the_production_dispatch_path(self):
        """The call chain, asserted so it cannot be quietly re-plumbed.

        `_drain_one` routes a mutation job to `_drain_mutation_one`, which
        invokes the registered `prepare_preconditions` -- and the export
        module registers `_prepare_preconditions_update` there. Each link
        is checked, because the run above would still pass if a future edit
        moved the assertion somewhere the drain no longer calls.
        """
        import inspect

        from odoo.addons.shopify_connector_core.models import (
            shopify_connector_job_dispatch as dispatch_module,
        )

        drain_one = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_one
        )
        self.assertIn('_is_mutation_job_type', drain_one)
        self.assertIn('_drain_mutation_one', drain_one)
        mutation = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_mutation_one
        )
        self.assertIn("strategy['prepare_preconditions']", mutation)

        strategies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_reconciliation_strategies()
        self.assertEqual(
            strategies[JOB_TYPE_UPDATE]['prepare_preconditions'].__name__,
            '_prepare_preconditions_update',
        )
        # Two hops, both asserted, because the guard sits behind the
        # confirmation assertion rather than being called directly by each
        # family -- which is the design, and is why every family reaches it.
        Service = self.env['shopify.connector.product.export.service']
        for job_type in (
            JOB_TYPE_CREATE, JOB_TYPE_UPDATE, JOB_TYPE_VARIANTS_CREATE,
            JOB_TYPE_VARIANTS_UPDATE, JOB_TYPE_BINDING_NAMESPACE,
            JOB_TYPE_MEDIA_STAGE, JOB_TYPE_MEDIA_FILE_CREATE,
            JOB_TYPE_MEDIA_ASSOCIATE,
        ):
            with self.subTest(family=job_type):
                source = inspect.getsource(
                    strategies[job_type]['prepare_preconditions']
                )
                self.assertTrue(
                    '_assert_preview_unexpired_pre_c2' in source
                    or '_assert_confirmed_preview_pre_c2' in source,
                    'This mutation family does not reach the TD-013 expiry '
                    'guard from the dispatcher.',
                )
        self.assertIn(
            '_assert_preview_unexpired_pre_c2',
            inspect.getsource(
                type(Service)._assert_confirmed_preview_pre_c2
            ),
            'The confirmation assertion is what carries every family into '
            'the expiry guard; if it stops calling it, all 8 families lose '
            'the check at once.',
        )
