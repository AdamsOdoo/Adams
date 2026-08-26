"""Batch 2 §9 -- consolidated vertical journeys, catalog side.

Journey C (product import), journey J-P0 (multi-store/company isolation) and
journey K-P0 (failure and recovery) driven end to end through production
routes only: an ordinary settings write of the kind the canonical Store
Settings form performs, the real `Import products now` button, the real cron,
the real scan handler, the real enqueue service, the real drain loop, the real
importer, the real decision dialog and the real resume.

ONE TRANSPORT, ROUTED BY QUERY. Both the catalog scan and the per-product
import go through the same `_send` seam, so the fixture below dispatches on
which query was sent. That is deliberate: a journey that patched the scan and
the importer separately could pass while the production code called something
else entirely in between.

WHAT MAKES THESE JOURNEYS RATHER THAN TESTS. Each one starts from a store an
operator has just configured and ends at a database consequence a merchant
could see -- a binding, a checkpoint, a job state -- with every step in
between performed by the same code the UI invokes. Where a step must fail,
it is made to fail by real data, never by an injected exception.
"""

import copy
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
STAMP_A = '2026-07-30T08:00:00Z'
STAMP_B = '2026-07-30T08:30:00Z'


class _FakeSendResponse:

    def __init__(self, body):
        self._body = body
        self.status_code = 200
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install')
class TestBatch2ProductJourneys(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Decision = cls.env['shopify.connector.product.match.decision']
        cls.Wizard = cls.env[
            'shopify.connector.product.match.decision.wizard'
        ]
        cls.TemplateBinding = cls.env[
            'shopify.connector.product.template.binding'
        ]
        cls.VariantBinding = cls.env[
            'shopify.connector.product.variant.binding'
        ]
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({
            'name': 'Batch2 Journeys Other Co',
        })
        cls.store = cls._make_store('journey-primary', cls.company)
        cls.foreign_store = cls._make_store(
            'journey-foreign', cls.other_company,
        )
        cls.roles = {
            label: cls._role_user(label, xmlid, cls.company)
            for label, xmlid in (
                ('auditor', 'group_shopify_connector_auditor'),
                ('operator', 'group_shopify_connector_operator'),
                ('reviewer', 'group_shopify_connector_reviewer'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }
        cls.foreign_admin = cls._role_user(
            'foreign-admin', 'group_shopify_connector_admin',
            cls.other_company,
        )

    @classmethod
    def _make_store(cls, slug, company):
        store = cls.env['shopify.connector.store'].create({
            'name': 'Journey %s' % slug,
            'shop_domain': '%s.myshopify.com' % slug,
            'api_version': '2026-07',
            'company_id': company.id,
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN,
        )
        cls.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
        })
        store.write({'state': 'connected'})
        return store

    @classmethod
    def _role_user(cls, label, xmlid, company):
        return cls.env['res.users'].create({
            'name': 'Journey %s' % label,
            'login': 'journey_%s' % label.replace('-', '_'),
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % xmlid).id,
            ])],
        })

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # the one transport
    # ------------------------------------------------------------------

    def _scan_page(self, nodes, has_next=False, end_cursor=None):
        return {'data': {'products': {
            'edges': [
                {'cursor': 'cur-%d' % index, 'node': node}
                for index, node in enumerate(nodes)
            ],
            'pageInfo': {'hasNextPage': has_next, 'endCursor': end_cursor},
        }}}

    def _scan_node(self, gid, updated_at=STAMP_A):
        return {'id': gid, 'updatedAt': updated_at, 'status': 'ACTIVE'}

    def _product_body(self, gid, variants, title=None, updated_at=STAMP_A):
        return {'data': {'product': {
            'id': gid,
            'title': title or 'Journey %s' % gid.rsplit('/', 1)[-1],
            'status': 'ACTIVE',
            'updatedAt': updated_at,
            'descriptionHtml': '',
            'vendor': '',
            'productType': '',
            'tags': [],
            'featuredImage': None,
            'options': [],
            'variants': {
                'nodes': variants,
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            },
        }}}

    def _variant(self, gid, sku=None, barcode=None):
        return {
            'id': gid, 'sku': sku, 'barcode': barcode,
            'price': '9.99', 'compareAtPrice': None,
            'selectedOptions': [], 'image': None,
            # Shopify inventory identity is per variant.  Reusing one fixed
            # InventoryItem GID made the second product collide with the
            # binding's store-scoped uniqueness constraint, turning this
            # journey into a retry rather than proving two independent
            # imports.
            'inventoryItem': {
                'id': 'gid://shopify/InventoryItem/%s' % (
                    gid.rsplit('/', 1)[-1],
                ),
            },
        }

    def _patch_transport(self, scan_pages=(), products=None):
        """Route by query, and record every request that was issued."""
        pages = list(scan_pages)
        products = products or {}
        sent = []
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            query = body.get('query') or ''
            sent.append(copy.deepcopy(body))
            if 'products(' in query:
                if not pages:
                    raise AssertionError('an unexpected extra scan page')
                return _FakeSendResponse(copy.deepcopy(pages.pop(0)))
            if 'product(' in query:
                gid = (body.get('variables') or {}).get('id')
                if gid not in products:
                    raise AssertionError(
                        'the importer asked for an unstubbed product %r' % gid
                    )
                return _FakeSendResponse(copy.deepcopy(products[gid]))
            raise AssertionError('unexpected query: %s' % query[:80])

        return patch.object(type(Client), '_send', fake_send), sent

    def _drain(self, scan_pages=(), products=None, limit=40):
        patcher, sent = self._patch_transport(scan_pages, products)
        self.env.flush_all()
        with patcher:
            self.Dispatch.run_drain(limit)
        return sent

    def _settings_of(self, store):
        return self.Settings.search([('store_id', '=', store.id)], limit=1)

    def _make_product(self, name, sku=None, company=None):
        template = self.env['product.template'].create({
            'name': name, 'company_id': company.id if company else False,
        })
        if sku:
            template.product_variant_id.write({'default_code': sku})
        return template

    def _jobs(self, store, job_type):
        return self.Job.search([
            ('store_id', '=', store.id), ('job_type', '=', job_type),
        ])

    # ==================================================================
    # JOURNEY C -- product import, configured to bound.
    # ==================================================================

    def test_journey_c_product_import_end_to_end(self):
        store, settings = self.store, self._settings_of(self.store)
        admin = self.roles['admin']
        operator = self.roles['operator']

        # --- 1. Configure product import through Store Settings ---------
        # Exactly the write the canonical form performs, as an
        # Administrator, through the ordinary model path.
        settings.with_user(admin).write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
            'product_scheduled_sync_enabled': True,
        })
        self.assertTrue(settings.product_domain_enabled)
        self.assertFalse(settings.product_last_import_checkpoint_at)

        # --- 2. Start a real enumeration through the production control --
        # `Import products now` on the store form, as an Operator.
        scan = store.with_user(operator).action_sync_products_now()
        self.assertEqual(scan.job_type, 'product_import_scan')
        self.assertEqual(scan.job_source, 'manual_sync')
        self.assertEqual(scan.state, 'queued')
        store.invalidate_recordset()
        self.assertTrue(store.product_sync_scheduled)
        self.assertEqual(store.product_sync_active_scan_count, 1)

        # --- 3. Two Odoo products; one Shopify product matches exactly
        #        one of them, the other matches two ---------------------
        clean = self._make_product('Journey Clean', sku='JC-CLEAN')
        dup_a = self._make_product('Journey Dup A', sku='JC-DUP')
        dup_b = self._make_product('Journey Dup B', sku='JC-DUP')

        clean_gid = 'gid://shopify/Product/J-CLEAN'
        dup_gid = 'gid://shopify/Product/J-DUP'

        # --- 4. Traverse scan -> children -> dispatcher -> importer -----
        sent = self._drain(
            scan_pages=[self._scan_page([
                self._scan_node(clean_gid), self._scan_node(dup_gid),
            ])],
            products={
                clean_gid: self._product_body(clean_gid, [
                    self._variant('%s-v' % clean_gid, sku='JC-CLEAN'),
                ]),
                dup_gid: self._product_body(dup_gid, [
                    self._variant('%s-v' % dup_gid, sku='JC-DUP'),
                ]),
            },
        )
        self.assertTrue(sent, 'nothing was ever sent -- no work was admitted')
        scan.invalidate_recordset()
        self.assertEqual(scan.state, 'succeeded')
        children = self._jobs(store, 'product_import_sync')
        self.assertEqual(len(children), 2)
        self.assertEqual(
            set(children.mapped('payload_hash')), {STAMP_A},
            'the child identity must be the verbatim remote stamp',
        )

        # --- 5. The unambiguous product completed -----------------------
        clean_job = children.filtered(
            lambda job: job.shopify_target_gid == clean_gid
        )
        self.assertEqual(clean_job.state, 'succeeded')
        clean_binding = self.TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', clean_gid),
        ])
        self.assertEqual(clean_binding.product_template_id, clean)
        self.assertEqual(clean_binding.match_key, 'sku_reference')

        # --- 6. The ambiguous one stopped, durably, with a decision -----
        dup_job = children.filtered(
            lambda job: job.shopify_target_gid == dup_gid
        )
        self.assertEqual(dup_job.state, 'blocked_manual_review')
        self.assertEqual(dup_job.manual_review_subreason, 'ambiguous_match')
        decision = self.Decision.search([('job_id', '=', dup_job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.state, 'pending')
        self.assertEqual(
            set(decision.candidate_template_ids.ids), {dup_a.id, dup_b.id},
        )
        self.assertTrue(dup_job.product_match_decision_pending)

        # The checkpoint DID advance -- the enumeration finished. The
        # blocked child is separate work with its own state, which is the
        # honest reading and the one the merchant sees on the store form.
        settings.invalidate_recordset()
        self.assertTrue(settings.product_last_import_checkpoint_at)
        self.assertTrue(settings.product_last_import_success_at)

        # --- 7. Resolve it through the real dialog ----------------------
        action = dup_job.with_user(
            self.roles['admin']
        ).action_open_product_match_decision()
        self.assertEqual(
            action['res_model'],
            'shopify.connector.product.match.decision.wizard',
        )
        wizard = self.Wizard.with_user(self.roles['admin']).with_context(
            action['context']
        ).create({})
        self.assertEqual(
            set(wizard.eligible_template_ids.ids), {dup_a.id, dup_b.id},
        )
        wizard.write({'selected_template_id': dup_b.id})
        wizard.action_confirm()

        # --- 8. The exact work resumed ---------------------------------
        dup_job.invalidate_recordset()
        self.assertEqual(dup_job.state, 'queued')
        self.assertEqual(
            len(self._jobs(store, 'product_import_scan')), 1,
            'resuming must not start a second catalog scan',
        )
        self.assertEqual(len(self._jobs(store, 'product_import_sync')), 2)

        self._drain(products={
            dup_gid: self._product_body(dup_gid, [
                self._variant('%s-v' % dup_gid, sku='JC-DUP'),
            ]),
        })

        # --- 9. The final binding, and the decision's own record --------
        dup_job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(dup_job.state, 'succeeded')
        dup_binding = self.TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', dup_gid),
        ])
        self.assertEqual(len(dup_binding), 1)
        self.assertEqual(dup_binding.product_template_id, dup_b)
        self.assertEqual(dup_binding.match_key, 'manual')
        self.assertEqual(dup_binding.matched_by_uid, self.roles['admin'])
        self.assertEqual(decision.state, 'consumed')
        self.assertEqual(decision.resulting_template_binding_id, dup_binding)
        self.assertEqual(decision.resolved_uid, self.roles['admin'])
        self.assertEqual(decision.resumed_job_state, 'queued')
        # And the store form now reports a completed sync with no scan in
        # flight.
        store.invalidate_recordset()
        self.assertEqual(store.product_sync_active_scan_count, 0)
        self.assertTrue(store.product_sync_last_checkpoint_at)

    def test_journey_c_scheduled_route_reaches_the_same_place(self):
        """The cron is a second door to the same room, not a second room."""
        store, settings = self.store, self._settings_of(self.store)
        settings.with_user(self.roles['admin']).write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
            'product_scheduled_sync_enabled': True,
        })
        self._make_product('Journey Cron Match', sku='JC-CRON')
        gid = 'gid://shopify/Product/J-CRON'
        self.env['shopify.connector.store']._cron_enqueue_product_scans()
        scans = self._jobs(store, 'product_import_scan')
        self.assertEqual(len(scans), 1)
        self.assertEqual(scans.job_source, 'scheduled_sync')
        self._drain(
            scan_pages=[self._scan_page([self._scan_node(gid)])],
            products={gid: self._product_body(
                gid, [self._variant('%s-v' % gid, sku='JC-CRON')],
            )},
        )
        binding = self.TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(len(binding), 1)

    def test_journey_c_refuses_to_start_when_the_domain_is_off(self):
        """The control is not offered, and the server refuses anyway."""
        store, settings = self.store, self._settings_of(self.store)
        settings.with_user(self.roles['admin']).write({
            'product_domain_enabled': False,
        })
        store.invalidate_recordset()
        self.assertFalse(store.product_sync_domain_enabled)
        with self.assertRaises(UserError):
            store.with_user(self.roles['operator']).action_sync_products_now()
        self.assertFalse(self._jobs(store, 'product_import_scan'))

    # ==================================================================
    # JOURNEY J-P0 -- multi-store and multi-company isolation.
    # ==================================================================

    def test_journey_j_two_companies_share_nothing(self):
        primary, foreign = self.store, self.foreign_store
        for store in (primary, foreign):
            self._settings_of(store).sudo().write({
                'product_domain_enabled': True,
                'product_first_sync_source': 'shopify_source',
            })
        # Same SKU, one product per company: each store's ambiguity is its
        # own, and neither store's candidate set may contain the other's.
        # Explicit companies on BOTH sides. A company-less product is
        # correctly shared by every company, so leaving the primary pair
        # neutral would make them legitimate candidates for the foreign store
        # too -- and the test would be measuring the fixture, not the rule.
        self._make_product('J Primary A', sku='J-SHARED', company=self.company)
        self._make_product('J Primary B', sku='J-SHARED', company=self.company)
        self._make_product(
            'J Foreign A', sku='J-SHARED', company=self.other_company,
        )
        self._make_product(
            'J Foreign B', sku='J-SHARED', company=self.other_company,
        )
        gid = 'gid://shopify/Product/J-ISO'
        body = self._product_body(
            gid, [self._variant('%s-v' % gid, sku='J-SHARED')],
        )
        for store in (primary, foreign):
            self.Job.create({
                'store_id': store.id,
                'job_source': 'scheduled_sync',
                'job_type': 'product_import_sync',
                'state': 'queued',
                'payload_hash': str(uuid.uuid4()),
                'shopify_target_gid': gid,
            })
        self._drain(products={gid: body})

        primary_decision = self.Decision.sudo().search([
            ('store_id', '=', primary.id),
        ])
        foreign_decision = self.Decision.sudo().search([
            ('store_id', '=', foreign.id),
        ])
        self.assertEqual(len(primary_decision), 1)
        self.assertEqual(len(foreign_decision), 1)

        # Each candidate set is its own company's, and nothing else.
        primary_names = primary_decision.candidate_template_ids.mapped('name')
        foreign_names = foreign_decision.candidate_template_ids.mapped('name')
        self.assertEqual(sorted(primary_names), ['J Primary A', 'J Primary B'])
        self.assertEqual(sorted(foreign_names), ['J Foreign A', 'J Foreign B'])

        # An administrator of one company is shown nothing of the other --
        # not the record, not its identity, not its count.
        as_primary = self.Decision.with_user(self.roles['admin'])
        self.assertEqual(as_primary.search_count([]), 1)
        self.assertEqual(as_primary.search([]), primary_decision)
        as_foreign = self.Decision.with_user(self.foreign_admin)
        self.assertEqual(as_foreign.search_count([]), 1)
        self.assertEqual(as_foreign.search([]), foreign_decision)
        with self.assertRaises(AccessError):
            foreign_decision.with_user(self.roles['admin']).read(['state'])

        # An action targeted at the wrong store's job is refused too.
        with self.assertRaises(AccessError):
            foreign_decision.job_id.with_user(
                self.roles['admin']
            ).action_open_product_match_decision()

    def test_journey_j_an_operator_cannot_scan_a_foreign_store(self):
        self._settings_of(self.foreign_store).sudo().write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        with self.assertRaises(AccessError):
            self.foreign_store.with_user(
                self.roles['operator']
            ).action_sync_products_now()
        self.assertFalse(
            self._jobs(self.foreign_store, 'product_import_scan'),
        )

    # ==================================================================
    # JOURNEY K-P0 -- failure and recovery.
    # ==================================================================

    def test_journey_k_safe_retry_works_unsafe_generic_retry_refuses(self):
        store = self.store
        self._settings_of(store).sudo().write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        # Batch 2 correction (F1/F2/F3): the complete journey runs on
        # PRODUCTION-SHAPED identity. A real Product GID carries a 13-digit
        # suffix and a real SKU is routinely all digits -- both rewritten by
        # the display scrubber, which is what made this journey's decision
        # unconsumable. `K-DUP` and `gid://shopify/Product/K-DUP` were two of
        # the few shapes that survived it.
        first = self._make_product('K Dup A', sku='1234567890123')
        self._make_product('K Dup B', sku='1234567890123')
        gid = 'gid://shopify/Product/7346299043911'
        job = self.Job.create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid,
        })
        body = self._product_body(
            gid,
            [self._variant(
                'gid://shopify/ProductVariant/45123456789012',
                sku='1234567890123',
            )],
        )
        self._drain(products={gid: body})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')

        # (a) The generic resolution refuses, and says what does work.
        with self.assertRaises(UserError) as ctx:
            job.with_user(
                self.roles['admin']
            ).action_resolve_manual_review()
        self.assertIn('match decision', str(ctx.exception))

        # (b) A blunt manual retry is technically permitted, and it cannot
        #     loop: it reproduces the same block against the same decision,
        #     without multiplying decisions.
        job.with_user(self.roles['admin']).action_manual_retry()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        self._drain(products={gid: body})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            self.Decision.search_count([('store_id', '=', store.id)]), 1,
        )

        # (c) The safe route resolves it, once, and the result is visible.
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['admin']).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': first.id})
        wizard.action_confirm()
        self._drain(products={gid: body})
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(decision.state, 'consumed')
        binding = self.TemplateBinding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(binding.product_template_id, first)

    def test_journey_k_a_concurrent_decision_refuses(self):
        store = self.store
        self._settings_of(store).sudo().write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        first = self._make_product('K Race A', sku='K-RACE')
        second = self._make_product('K Race B', sku='K-RACE')
        gid = 'gid://shopify/Product/K-RACE'
        self.Job.create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid,
        })
        self._drain(products={gid: self._product_body(
            gid, [self._variant('%s-v' % gid, sku='K-RACE')],
        )})
        decision = self.Decision.search([('store_id', '=', store.id)])
        self.assertEqual(len(decision), 1)
        # Two administrators open the same decision.
        reviewer_wizard = self.Wizard.with_user(
            self.roles['admin']
        ).with_context(default_decision_id=decision.id).create({
            'selected_template_id': first.id,
        })
        admin_wizard = self.Wizard.with_user(
            self.roles['admin']
        ).with_context(default_decision_id=decision.id).create({
            'selected_template_id': second.id,
        })
        reviewer_wizard.action_confirm()
        with self.assertRaises(UserError):
            admin_wizard.action_confirm()
        decision.invalidate_recordset()
        self.assertEqual(decision.selected_template_id, first)
        self.assertEqual(decision.resolved_uid, self.roles['admin'])

    def test_journey_k_a_failed_scan_leaves_the_checkpoint_alone(self):
        store, settings = self.store, self._settings_of(self.store)
        settings.sudo().write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
            'product_last_import_checkpoint_at': fields.Datetime.to_datetime(
                '2026-07-01 00:00:00',
            ),
        })
        before = settings.product_last_import_checkpoint_at
        scan = store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        # A malformed second page: page one's children are discarded with it.
        self._drain(scan_pages=[
            self._scan_page(
                [self._scan_node('gid://shopify/Product/K-FAIL-1')],
                has_next=True, end_cursor='NEXT',
            ),
            {'data': {'products': {'edges': 'not-a-list',
                                   'pageInfo': {'hasNextPage': False,
                                                'endCursor': None}}}},
        ])
        scan.invalidate_recordset()
        settings.invalidate_recordset()
        self.assertNotEqual(scan.state, 'succeeded')
        self.assertEqual(
            settings.product_last_import_checkpoint_at, before,
            'a failed enumeration advanced the checkpoint',
        )
        self.assertFalse(self._jobs(store, 'product_import_sync'))
