"""TD-012: the first-push ceremony is reachable from production.

The defect
----------
`first_push_state` is written to `previewed` in exactly one place — the
`inventory_first_push_preview` handler — and that job type had exactly one
admission surface, `_enqueue_first_push_preview`, which had **zero
production callers**. Not a button, not a cron, not a wizard, not an RPC
path. A pair created in `pending` could never leave it.

Everything downstream was correct and unreachable. `action_confirm_first_push`
refuses any state but `previewed`; the Confirm control is rendered only in
`previewed`; `inventory_push_sync` refuses every mutation until `confirmed`.
So the entire first-push safety ceremony — the one DEC-007/DEC-010 require
before Odoo may overwrite a merchant's live Shopify stock — was a closed
loop with no entrance.

The shipped UI stated the trigger plainly, in the `pending` empty state:

    "The preview runs on the next scheduled pass; the confirmation control
     appears once it has."

That sentence named the correct design and no code implemented it. The
correction makes the sentence true rather than rewriting it, so the scan
that was already running for every push-enabled binding now admits the
preview for pairs still in `pending`.

These tests drive production surfaces only. No test here writes
`first_push_state` by hand — that habit is precisely why every existing
test passed while the flow was unreachable.
"""

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestInventoryFirstPushReachability(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.inventory.service']
        cls.Job = cls.env['shopify.connector.job']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'First Push Reach Store',
            'shop_domain': 'first-push-reach.myshopify.com',
            'api_version': '2026-07',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'First Push Reach Location',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        cls.mapping = cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/REACH',
            'odoo_location_id': cls.location.id,
            'match_key': 'manual',
            'push_enabled': True,
        })
        cls.template = cls.env['product.template'].create({
            'name': 'First Push Reach Product',
        })
        template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/REACH',
            'product_template_id': cls.template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/REACH',
            'product_variant_id': cls.template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Reach Operator',
            'login': 'first_push_reach_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })
        cls.user_reviewer = cls.env['res.users'].create({
            'name': 'Reach Reviewer',
            'login': 'first_push_reach_reviewer',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })
        cls.user_auditor = cls.env['res.users'].create({
            'name': 'Reach Auditor',
            'login': 'first_push_reach_auditor',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _pending_binding(self, gid='gid://shopify/InventoryItem/REACH'):
        """A pair in a GENUINE `pending` state — the model's own default.

        Deliberately does not pass `first_push_state`. A fixture that sets
        it is a fixture that cannot notice the state is unreachable.
        """
        binding = self.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create({
            'store_id': self.store.id,
            'product_variant_binding_id': self.variant_binding.id,
            'location_mapping_id': self.mapping.id,
            'shopify_inventory_item_gid': gid,
        })
        self.assertEqual(
            binding.first_push_state, 'pending',
            'The default must be `pending`; this suite depends on it.',
        )
        return binding

    def _run_scan(self):
        """Run the real scheduled pass: cron entry point, then its job."""
        scan_jobs = self.Service.run_inventory_push_scan()
        scan_jobs = scan_jobs.filtered(lambda j: j.store_id == self.store)
        self.assertTrue(
            scan_jobs, 'The cron did not enqueue a scan for this store.',
        )
        for job in scan_jobs:
            job.sudo().write({'state': 'running'})
            self.Service._handle_inventory_push_scan(job)
        return scan_jobs

    def _preview_jobs(self, binding):
        return self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_first_push_preview'),
            ('res_id', '=', binding.id),
        ])

    def _push_sync_jobs(self, binding):
        return self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_push_sync'),
            ('res_id', '=', binding.id),
        ])

    # ------------------------------------------------------------------
    # The scheduled route the UI promises
    # ------------------------------------------------------------------

    def test_the_scheduled_pass_admits_a_preview_for_a_pending_pair(self):
        binding = self._pending_binding()
        self.assertFalse(
            self._preview_jobs(binding),
            'Nothing may exist before the scan runs.',
        )
        self._run_scan()
        self.assertEqual(
            len(self._preview_jobs(binding)), 1,
            'The scheduled pass must admit exactly one first-push preview '
            'for a pair still awaiting one. Without this the pair can never '
            'leave `pending` and the whole ceremony is unreachable.',
        )

    def test_the_scheduled_pass_admits_no_push_sync_for_a_pending_pair(self):
        """Preview INSTEAD OF push, for two independent reasons.

        Semantically an unconfirmed pair has nothing to push. Mechanically
        both job types share the pair's `operation_scope_key`, so admitting
        both would collide on the unique constraint and one would vanish
        into the coalesce path.
        """
        binding = self._pending_binding()
        self._run_scan()
        self.assertFalse(
            self._push_sync_jobs(binding),
            'A pair that has not been previewed has nothing to push; '
            'admitting a push job for it can only ever decline, and it '
            'would take the pair scope key the preview needs.',
        )

    def test_a_confirmed_pair_still_gets_its_push_sync(self):
        """No regression: the scan's original job is untouched."""
        binding = self._pending_binding()
        self._run_scan()
        preview = self._preview_jobs(binding)
        preview.sudo().write({'state': 'running'})
        self.Service._handle_inventory_first_push_preview(preview)
        binding.with_user(self.user_reviewer).action_confirm_first_push()
        self.assertEqual(binding.first_push_state, 'confirmed')

        self._run_scan()
        self.assertTrue(
            self._push_sync_jobs(binding),
            'Once confirmed, the pair must re-enter ordinary push '
            'orchestration.',
        )

    def test_a_second_scan_does_not_admit_a_duplicate_preview(self):
        binding = self._pending_binding()
        self._run_scan()
        self._run_scan()
        self.assertEqual(
            len(self._preview_jobs(binding)), 1,
            'A non-terminal job already holds this pair scope; a second '
            'scan must coalesce, not stack previews.',
        )

    def test_scan_refreshes_previewed_pair_without_admitting_push(self):
        binding = self._pending_binding()
        self._run_scan()
        first = self._preview_jobs(binding)
        first.sudo().write({'state': 'running'})
        self.Service._handle_inventory_first_push_preview(first)
        self.assertEqual(binding.first_push_state, 'previewed')

        self._run_scan()
        previews = self._preview_jobs(binding)
        self.assertEqual(len(previews), 2)
        self.assertEqual(len(previews.filtered(lambda job: job.state == 'queued')), 1)
        self.assertFalse(self._push_sync_jobs(binding))

    def test_the_preview_job_moves_a_pending_pair_to_previewed(self):
        """The production handler, on a production-admitted job."""
        binding = self._pending_binding()
        self._run_scan()
        job = self._preview_jobs(binding)
        job.sudo().write({'state': 'running'})
        self.Service._handle_inventory_first_push_preview(job)
        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_state, 'previewed')
        self.assertEqual(job.state, 'succeeded')

    def test_the_preview_issues_no_shopify_request(self):
        """Requirement 5: preview is a read of Odoo, never a mutation."""
        binding = self._pending_binding()
        self._run_scan()
        job = self._preview_jobs(binding)
        job.sudo().write({'state': 'running'})
        Client = type(self.env['shopify.connector.api.client'])
        with patch.object(Client, '_send') as sent:
            self.Service._handle_inventory_first_push_preview(job)
        sent.assert_not_called()
        self.assertEqual(job.job_source, 'export_preview_dry_run')

    def test_the_full_ceremony_runs_through_production_surfaces_only(self):
        """pending -> previewed -> confirmed, nothing fabricated.

        The assertion the previous suite could not make: no step here
        writes `first_push_state`, and the pair still arrives at
        `confirmed`.
        """
        binding = self._pending_binding()

        self._run_scan()
        job = self._preview_jobs(binding)
        job.sudo().write({'state': 'running'})
        self.Service._handle_inventory_first_push_preview(job)
        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_state, 'previewed')

        binding.with_user(self.user_reviewer).action_confirm_first_push()
        binding.invalidate_recordset()
        self.assertEqual(binding.first_push_state, 'confirmed')
        self.assertTrue(binding.first_push_confirmed_at)
        self.assertTrue(binding.first_push_confirmed_by_uid)

    def test_the_preview_does_not_become_an_unconfirmed_push(self):
        """Requirement 9: previewing must not grant push authority."""
        binding = self._pending_binding()
        self._run_scan()
        job = self._preview_jobs(binding)
        job.sudo().write({'state': 'running'})
        self.Service._handle_inventory_first_push_preview(job)
        binding.invalidate_recordset()
        self.assertEqual(
            binding.first_push_state, 'previewed',
            'A preview records a quantity; it never confirms anything.',
        )
        self.assertFalse(binding.first_push_confirmed_at)
        self.assertFalse(binding.first_push_confirmed_by_uid)
        self.assertFalse(
            binding.last_pushed_at,
            'Nothing may have been pushed by a preview.',
        )

    # ------------------------------------------------------------------
    # The manual admission keeps its role matrix
    # ------------------------------------------------------------------

    def test_an_operator_may_admit_a_preview_manually(self):
        binding = self._pending_binding()
        job = self.Service.with_user(
            self.user_operator
        )._enqueue_first_push_preview(binding)
        self.assertEqual(job.job_type, 'inventory_first_push_preview')

    def test_an_auditor_may_not_admit_a_preview(self):
        binding = self._pending_binding()
        with self.assertRaises(AccessError):
            self.Service.with_user(
                self.user_auditor
            )._enqueue_first_push_preview(binding)
        self.assertFalse(self._preview_jobs(binding))

    def test_the_manual_admission_refuses_another_company(self):
        """Requirement 3: company isolation is checked BEFORE the elevation.

        Holding the Operator group is authority within your own companies,
        not everywhere. The admission runs under `sudo()` once it starts,
        so the company check has to happen in front of it.
        """
        other_company = self.env['res.company'].create({
            'name': 'First Push Reach Other Co',
        })
        binding = self._pending_binding()
        binding.sudo().write({'company_id': other_company.id})
        self.assertNotIn(other_company, self.user_operator.company_ids)
        with self.assertRaises(AccessError):
            self.Service.with_user(
                self.user_operator
            )._enqueue_first_push_preview(binding)
        self.assertFalse(self._preview_jobs(binding))

    def test_the_manual_admission_coalesces_rather_than_duplicating(self):
        binding = self._pending_binding()
        first = self.Service.with_user(
            self.user_operator
        )._enqueue_first_push_preview(binding)
        second = self.Service.with_user(
            self.user_operator
        )._enqueue_first_push_preview(binding)
        self.assertTrue(first)
        self.assertFalse(
            second,
            'A pair already holding a non-terminal preview job must '
            'coalesce, not stack a second one.',
        )

    # ------------------------------------------------------------------
    # Structural: the surface may not become orphaned again
    # ------------------------------------------------------------------

    def test_the_preview_admission_has_a_production_caller(self):
        """The exact defect, asserted so it cannot silently return.

        `_enqueue_first_push_preview` was correct code with no caller. A
        test that only exercises it directly cannot tell the difference
        between reachable and unreachable, which is why this one looks at
        the production source instead.
        """
        import inspect

        from ..models import shopify_connector_inventory_service as service

        source = inspect.getsource(service)
        # Strip the definitions themselves so only genuine call sites count.
        call_sites = [
            line for line in source.splitlines()
            if '_admit_first_push_preview(' in line
            and not line.strip().startswith('def ')
        ]
        self.assertTrue(
            any('self._admit_first_push_preview(binding)' in line
                for line in call_sites),
            'No production code path admits a first-push preview, so no '
            'pair can ever leave `pending` (TD-012).',
        )
        scan = inspect.getsource(service.ShopifyConnectorInventoryService
                                 ._handle_inventory_push_scan)
        self.assertIn(
            '_admit_first_push_preview', scan,
            'The scheduled pass is the trigger the shipped UI promises in '
            'its `pending` empty state. If that moves, update the UI copy '
            'in the same commit.',
        )
