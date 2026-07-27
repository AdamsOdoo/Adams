"""TD-011: a media export that stopped can be resumed exactly once per try.

The defect
----------
Every media job built its `payload_hash` from `<step>:<checksum>` alone.
Core derives `idempotency_key` from that hash and — unlike
`operation_scope_key` — **never clears it**, deliberately, because that is
what makes it a durable replay guard past a job's terminal state.

The consequence was that the first failure of an image export was
permanent. A second attempt produced a byte-identical `idempotency_key`
and collided on `(store_id, idempotency_key)`. There was no way out of it:
the media row cannot be unlinked (it is the only evidence of which remote
Files this connector created), and the per-checksum unique index refuses a
replacement row. So a merchant whose image upload failed once could never
export that image again, and under `_dispatch_one` the `23505` surfaced
during the enclosing flush and ended the drain pass for every unrelated
store in it.

The correction
--------------
A `resume_attempt` ordinal on the row, included in the payload hash. That
is the whole mechanism, and it is chosen because it distinguishes the two
things that were conflated:

* **re-dispatching the job already admitted** — same row, same ordinal,
  same key. Deterministic replay, unchanged.
* **an authorised new attempt after the last one stopped** — new ordinal,
  new key, its own durable identity.

`(store_id, idempotency_key)` is not weakened for anything, anywhere. No
history is rewritten: the previous job keeps its key, its logs and its
attempts, and the row keeps its checksum, filename and remote GID.
"""

import base64
import uuid
from unittest.mock import patch

from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)

from ..models.shopify_connector_media_export_service import (
    JOB_TYPE_MEDIA_ASSOCIATE,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_POLL,
    JOB_TYPE_MEDIA_STAGE,
    image_checksum,
)
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from .common import ExportCase, FILE_GID, PRODUCT_GID
from .test_media_export_pipeline import PNG_1X1


@tagged('post_install', '-at_install')
class TestMediaResume(ExportCase):

    def setUp(self):
        super().setUp()
        self.binding = self.bind_template()
        self.settings.sudo().write({'media_source_of_truth': 'odoo'})
        self.template.write({'image_1920': PNG_1X1})
        self.checksum = image_checksum(base64.b64decode(PNG_1X1))
        self.Job = self.env['shopify.connector.job']

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

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

    def _row(self, remote_status='staged', **extra):
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

    def _jobs_for(self, row, job_type=None):
        domain = [
            ('store_id', '=', self.store.id),
            ('res_model', '=', row._name),
            ('res_id', '=', row.id),
        ]
        if job_type:
            domain.append(('job_type', '=', job_type))
        return self.Job.sudo().search(domain)

    def _terminate(self, job, state='failed_final'):
        job.sudo().write({'state': state})
        self.env.flush_all()

    def _uncertain_attempt(self, job):
        """An attempt with an unestablished outcome, built the real way.

        Mutation attempts are creatable only through the Layer 2 C2
        surface and their outcomes are immutable once machine-observed, so
        the fixture goes through `_create_attempt_intent` and
        `_record_direct_outcome` rather than writing the columns. A
        fixture that bypassed those guards would not be testing the state
        production can actually reach.
        """
        # C2 refuses an intent unless the job is genuinely running and owns
        # the token, which is the state a real transport is admitted from.
        token = uuid.uuid4().hex
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        self.env.flush_all()
        attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation':
                job.store_id.connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
            'remote_mutation_intent': {'job_id': job.id},
            'preconditions_snapshot': {},
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        return attempt._record_direct_outcome('uncertain')

    # ------------------------------------------------------------------
    # 1. Retry of the same job stays deterministic
    # ------------------------------------------------------------------

    def test_readmitting_the_same_step_is_the_same_job(self):
        """Requirement 2: replay of one admitted job is unchanged.

        Two admissions with no resume between them must resolve to the
        SAME job record, not a second one and not an error. That is what
        makes a re-dispatch idempotent.
        """
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        second = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        self.assertEqual(first, second)
        self.assertEqual(
            len(self._jobs_for(first.res_id and self.MediaBinding.browse(
                first.res_id), JOB_TYPE_MEDIA_STAGE)), 1,
        )

    def test_the_payload_hash_is_stable_within_one_attempt(self):
        row = self._row()
        self.assertEqual(
            self.Media._media_payload_hash(row, JOB_TYPE_MEDIA_STAGE),
            self.Media._media_payload_hash(row, JOB_TYPE_MEDIA_STAGE),
        )

    # ------------------------------------------------------------------
    # 2. A resume gets its own durable identity
    # ------------------------------------------------------------------

    def test_a_resume_after_a_terminal_pre_transport_failure_is_admitted(self):
        """The headline case: the export failed and can start again."""
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        self._terminate(first)

        resumed = self.Media._resume_media_export(row)
        self.assertTrue(
            resumed,
            'A failed image export must be resumable. Before TD-011 this '
            'collided on (store_id, idempotency_key) forever.',
        )
        self.assertNotEqual(resumed, first)
        self.assertNotEqual(
            resumed.idempotency_key, first.idempotency_key,
            'The resume needs its OWN durable identity, or it is the same '
            'permanent collision by another name.',
        )
        row.invalidate_recordset()
        self.assertEqual(row.resume_attempt, 1)

    def test_a_repeated_resume_request_keeps_advancing(self):
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        keys = {first.idempotency_key}
        for expected in (1, 2, 3):
            self._terminate(self._jobs_for(row).filtered(
                lambda j: j.state not in ('failed_final', 'succeeded')
            ) or first)
            job = self.Media._resume_media_export(row)
            row.invalidate_recordset()
            self.assertEqual(row.resume_attempt, expected)
            self.assertNotIn(
                job.idempotency_key, keys,
                'Every authorised resume needs a distinct identity.',
            )
            keys.add(job.idempotency_key)

    def test_a_resume_after_a_failed_non_associated_step_re_enters_correctly(self):
        """Requirement: resume from where the row actually got to."""
        cases = {
            'staged': JOB_TYPE_MEDIA_STAGE,
            'uploaded': JOB_TYPE_MEDIA_FILE_CREATE,
            'processing': JOB_TYPE_MEDIA_POLL,
            'ready': JOB_TYPE_MEDIA_ASSOCIATE,
        }
        for index, (status, expected_step) in enumerate(sorted(cases.items())):
            with self.subTest(remote_status=status):
                checksum = image_checksum(
                    base64.b64decode(PNG_1X1) + bytes([index])
                )
                row = self._row(
                    remote_status=status,
                    odoo_image_checksum=checksum,
                    connector_filename=self.Media._connector_filename(
                        self.template.id, checksum,
                    ),
                    shopify_gid=(
                        FILE_GID + str(index) if status in
                        ('processing', 'ready') else 'pending:%d' % index
                    ),
                    staged_resource_url=(
                        'https://example.invalid/s%d' % index
                        if status == 'uploaded' else False
                    ),
                )
                self._applying_preview()
                job = self.Media._resume_media_export(row)
                self.assertTrue(job)
                self.assertEqual(
                    job.job_type, expected_step,
                    'A resume must re-enter the chain where the row got '
                    'to, not restart a step whose remote effect already '
                    'happened.',
                )

    # ------------------------------------------------------------------
    # 3. What a resume must refuse
    # ------------------------------------------------------------------

    def test_an_already_associated_image_is_never_resumed(self):
        """Requirement 7: no duplicate Shopify media association.

        The pipeline is append-only and `referencesToRemove` is never
        sent, so a second association is not correctable afterwards.
        """
        self._applying_preview()
        row = self._row(remote_status='associated', shopify_gid=FILE_GID)
        job = self.Media._resume_media_export(row)
        self.assertFalse(job)
        row.invalidate_recordset()
        self.assertIn('already associated', row.resume_blocked_reason)
        self.assertEqual(
            row.resume_attempt, 0,
            'A refused resume must not consume an attempt identity.',
        )

    def test_an_ambiguous_previous_outcome_blocks_a_new_mutation(self):
        """Requirement 8: reconcile before admitting another mutation.

        An `uncertain` attempt means the connector does not know whether
        Shopify applied the call. Admitting a resume on top of that is how
        one uncertain mutation becomes two real ones.
        """
        preview = self._applying_preview()
        job = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(job.res_id)
        self._uncertain_attempt(job)
        # The state an uncertain outcome actually parks a job in: held for
        # manual review, with the subreason the model requires.
        job.sudo().write({
            'state': 'blocked_manual_review',
            'manual_review_subreason': 'idempotency_contract_violation',
        })
        self.env.flush_all()

        resumed = self.Media._resume_media_export(row)
        self.assertFalse(
            resumed,
            'A resume may not be admitted while the previous attempt has '
            'no established outcome.',
        )
        row.invalidate_recordset()
        self.assertIn('reconciled', row.resume_blocked_reason)
        self.assertEqual(row.resume_attempt, 0)

    def test_a_resolved_ambiguous_outcome_no_longer_blocks(self):
        """Once reconciled, the resume proceeds. The gate is not a wall."""
        preview = self._applying_preview()
        job = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(job.res_id)
        attempt = self._uncertain_attempt(job)
        attempt._record_reconciliation_result('not_applied', {})
        self._terminate(job)
        self.assertTrue(self.Media._resume_media_export(row))

    def test_a_resume_without_an_authorising_preview_is_refused(self):
        row = self._row(remote_status='failed')
        self.assertFalse(self.Media._resume_media_export(row))
        row.invalidate_recordset()
        self.assertIn('authorises', row.resume_blocked_reason)

    # ------------------------------------------------------------------
    # 4. Nothing is destroyed or rewritten
    # ------------------------------------------------------------------

    def test_a_resume_preserves_the_old_job_and_the_media_evidence(self):
        """Requirements 5, 6 and 9, asserted together.

        The previous job keeps its identity and its logs; the row keeps
        its checksum, filename and whatever remote GID it reached. A
        resume adds history, it never edits it.
        """
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        row.sudo().write({'shopify_gid': FILE_GID, 'remote_status': 'ready'})
        original_key = first.idempotency_key
        original_checksum = row.odoo_image_checksum
        original_filename = row.connector_filename
        self._terminate(first)

        self.Media._resume_media_export(row)

        first.invalidate_recordset()
        row.invalidate_recordset()
        self.assertTrue(
            first.exists(), 'The previous job row must survive a resume.',
        )
        self.assertEqual(
            first.idempotency_key, original_key,
            'Historic audit identity may never be rewritten to make room '
            'for a new attempt.',
        )
        self.assertEqual(row.odoo_image_checksum, original_checksum)
        self.assertEqual(row.connector_filename, original_filename)
        self.assertEqual(
            row.shopify_gid, FILE_GID,
            'The remote-GID evidence must survive the resume.',
        )

    def test_the_uniqueness_constraint_is_not_weakened(self):
        """Requirement 4: the guard still guards.

        Two jobs that genuinely ARE the same operation, same target, same
        payload and same attempt must still be one job.
        """
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        again = self.Media._admit_media_job(
            self.store, JOB_TYPE_MEDIA_STAGE, row, PRODUCT_GID,
        )
        self.assertEqual(first, again)
        self.assertEqual(len(self._jobs_for(row, JOB_TYPE_MEDIA_STAGE)), 1)

    def test_no_media_row_is_ever_unlinked_by_a_resume(self):
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        before = self.MediaBinding.sudo().search_count([
            ('store_id', '=', self.store.id),
        ])
        self._terminate(first)
        self.Media._resume_media_export(row)
        self.assertEqual(
            self.MediaBinding.sudo().search_count([
                ('store_id', '=', self.store.id),
            ]),
            before,
            'A resume reuses the ownership row; it neither deletes nor '
            'duplicates it.',
        )

    # ------------------------------------------------------------------
    # 5. Containment: an unrelated store keeps its turn
    # ------------------------------------------------------------------

    def test_a_duplicate_admission_does_not_poison_the_transaction(self):
        """Requirement 10.

        Before TD-011 the duplicate surfaced as a `23505` during the
        enclosing flush, which aborts the PostgreSQL transaction — so the
        drain pass died and every other store queued behind it lost its
        turn. Proving the transaction is still usable afterwards is the
        assertion that matters; a swallowed error that left the cursor
        aborted would fail here.
        """
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        self.Media._admit_media_job(
            self.store, JOB_TYPE_MEDIA_STAGE, row, PRODUCT_GID,
        )
        # The transaction must still be usable for unrelated work.
        other = self.env['shopify.connector.store'].sudo().create({
            'name': 'TD-011 unrelated store',
            'shop_domain': 'td011-unrelated.myshopify.com',
            'api_version': SHOPIFY_API_VERSION,
        })
        self.assertTrue(other.exists())
        self.assertEqual(
            self.MediaBinding.sudo().search_count([('id', '=', row.id)]), 1,
        )

    def test_the_resume_issues_no_shopify_request(self):
        """Admission is bookkeeping. The transport is a separate job."""
        preview = self._applying_preview()
        first = self.Media._enqueue_media_step(
            preview, {'step': JOB_TYPE_MEDIA_STAGE, 'role': 'primary',
                      'checksum': self.checksum, 'odoo_variant_id': False},
        )
        row = self.MediaBinding.browse(first.res_id)
        self._terminate(first)
        Client = type(self.env['shopify.connector.api.client'])
        with patch.object(Client, '_send') as sent:
            self.Media._resume_media_export(row)
        sent.assert_not_called()

    # ------------------------------------------------------------------
    # 6. Structural
    # ------------------------------------------------------------------

    def test_every_media_admission_carries_the_attempt_ordinal(self):
        """No media job may be admitted with a bare deterministic hash.

        The original defect in one assertion: if a future edit builds a
        media `payload_hash` without the resume ordinal, that step becomes
        permanently un-resumable again.
        """
        import inspect

        from ..models import shopify_connector_media_export_service as media

        source = inspect.getsource(media)
        # The only sanctioned producer is `_media_payload_hash`. Anything
        # that derives a media job's hash from the checksum directly is the
        # original defect returning.
        offenders = [
            line.strip() for line in source.splitlines()
            if 'odoo_image_checksum' in line and 'payload_hash' in line
        ]
        self.assertIn(
            'payload_hash = self._media_payload_hash(row, step_type)',
            source,
            'The single admission point must derive its hash from the '
            'ordinal-bearing helper.',
        )
        self.assertFalse(offenders, (
            'These media admissions build a payload hash without the '
            'resume ordinal, so a failed attempt could never be resumed '
            '(TD-011): %s' % offenders
        ))
