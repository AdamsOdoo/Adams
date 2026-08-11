"""Batch 2 §8.3 -- the durable product and variant match decision.

Every test in this file drives a PRODUCTION route. The ambiguity is produced
by the real importer, routed by the real dispatcher, recorded by the real
`_route_failure` seam, decided through the real wizard, and resumed through
the real `action_manual_retry`. Transport is patched at `_send` -- the single
seam every Shopify call in this module passes through -- so no test can reach
Shopify even by accident, and a test asserting "no mutation" is asserting
something structural rather than something hoped for.

TWO THINGS THIS FILE IS CAREFUL ABOUT.

*Work must be admitted.* A test that asserts "no binding was created" passes
brilliantly against a run in which the importer was never invoked at all.
Every end-to-end test here asserts the job actually moved, that the transport
was actually called, and what the database actually holds afterwards.

*Controls are proved by their own absence.* The load-bearing claims at the
bottom mutate the production code -- remove the identity check, remove the
eligibility recomputation, write the decision inside the importer's savepoint
-- and assert that the specific test claiming each one fails.
"""

import copy
import hashlib
import json
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from ..models.shopify_connector_product_match_decision import (
    DECISION_LEVEL_TEMPLATE,
    DECISION_LEVEL_VARIANT,
    MATCH_CANDIDATE_LIMIT,
    MATCH_DIGEST_LEN,
    MATCH_EVIDENCE_KEYS,
    MATCH_GID_MAX_LEN,
    MATCH_IDENTIFIER_MAX_LEN,
    MATCH_TITLE_MAX_LEN,
    MATCH_VALUES_LIMIT,
    build_match_evidence,
    decision_key_for,
    match_value_digest,
    opaque_identity,
    parse_match_evidence,
    safe_match_preview,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
REMOTE_STAMP = '2026-07-30T09:15:00Z'
LATER_STAMP = '2026-07-30T11:45:00Z'


class _FakeSendResponse:
    """Minimal `requests.Response` stand-in for the `_send` transport seam."""

    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


# Issue #193 / #157 -- Odoo 19 test-phase contract. These fixtures insert rows
# into business tables whose NOT NULL columns are contributed by modules
# outside this module's dependency closure, which only exist on the model at
# post_install. See docs/05-qa/odoo19-test-phase-contract.md.
@tagged('post_install', '-at_install')
class TestProductMatchDecision(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Decision = cls.env['shopify.connector.product.match.decision']
        cls.Wizard = cls.env[
            'shopify.connector.product.match.decision.wizard'
        ]
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env[
            'shopify.connector.product.template.binding'
        ]
        cls.VariantBinding = cls.env[
            'shopify.connector.product.variant.binding'
        ]
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({
            'name': 'Shopify Match Decision Other Co',
        })
        cls.store = cls._make_store(
            'Match Decision Store', 'match-decision', cls.company,
        )
        cls.other_store = cls._make_store(
            'Match Decision Foreign Store', 'match-decision-foreign',
            cls.other_company,
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
            'foreign_admin', 'group_shopify_connector_admin',
            cls.other_company,
        )

    @classmethod
    def _make_store(cls, name, slug, company):
        store = cls.env['shopify.connector.store'].create({
            'name': name,
            'shop_domain': '%s.myshopify.com' % slug,
            'api_version': '2026-07',
            'company_id': company.id,
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN,
        )
        cls.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        store.write({'state': 'connected'})
        return store

    @classmethod
    def _role_user(cls, label, xmlid, company):
        return cls.env['res.users'].create({
            'name': 'Match decision %s' % label,
            'login': 'match_decision_%s' % label,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % xmlid).id,
            ])],
        })

    def setUp(self):
        super().setUp()
        # `execute_business._admit` runs its gate/lease on a
        # `registry.cursor()` side transaction; under a plain TransactionCase
        # that cursor cannot see this test's uncommitted fixture, so admission
        # would fail closed. Registry test mode makes every `registry.cursor()`
        # reuse the single test connection -- the sanctioned core-test
        # mechanism, changing no production behaviour.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------

    def _make_product(self, name, sku=None, barcode=None, company=None):
        template = self.env['product.template'].create({
            'name': name,
            'company_id': company.id if company else False,
        })
        variant = template.product_variant_id
        vals = {}
        if sku:
            vals['default_code'] = sku
        if barcode:
            vals['barcode'] = barcode
        if vals:
            variant.write(vals)
        return template, variant

    def _graphql_product(
        self, gid, variants, title='Ambiguous Product',
        updated_at=REMOTE_STAMP, options=None,
    ):
        return {
            'data': {'product': {
                'id': gid,
                'title': title,
                'status': 'ACTIVE',
                'updatedAt': updated_at,
                'descriptionHtml': '',
                'vendor': '',
                'productType': '',
                'tags': [],
                'featuredImage': None,
                'options': options or [],
                'variants': {
                    'nodes': variants,
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                },
            }},
        }

    def _graphql_variant(self, gid, sku=None, barcode=None):
        return {
            'id': gid, 'sku': sku, 'barcode': barcode,
            'price': '19.99', 'compareAtPrice': None,
            'selectedOptions': [], 'image': None,
            'inventoryItem': {'id': 'gid://shopify/InventoryItem/1'},
        }

    def _import_job(self, gid, store=None, payload_hash=None):
        store = store or self.store
        job = self.Job.create({
            'store_id': store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': payload_hash or str(uuid.uuid4()),
            'shopify_target_gid': gid,
        })
        self.env.flush_all()
        return job

    def _patch_send(self, body):
        """Patch the one transport seam and record every request issued.

        Each call gets its OWN deep copy of the fixture. A real transport
        returns a freshly parsed body every time, and the importer normalises
        in place; handing every call the same dict lets one job's parse
        corrupt the next job's payload, which shows up as a bogus
        `data_shape_schema_mismatch` several tests later.
        """
        sent = []
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, request_body, token=None):
            request_body = request_body or {}
            sent.append(copy.deepcopy(request_body))
            return _FakeSendResponse(copy.deepcopy(body))

        return patch.object(type(Client), '_send', fake_send), sent

    def _drain(self, body):
        """Run the REAL drain loop with the transport patched."""
        patcher, sent = self._patch_send(body)
        self.env.flush_all()
        with patcher:
            self.Dispatch.run_drain(20)
        return sent

    def _ambiguous_template_run(self, gid='gid://shopify/Product/8201',
                                sku='DUP-TPL', updated_at=REMOTE_STAMP):
        """Two Odoo products share a SKU; import the Shopify product."""
        first, _ = self._make_product('Ambiguous A', sku=sku)
        second, _ = self._make_product('Ambiguous B', sku=sku)
        job = self._import_job(gid)
        sent = self._drain(self._graphql_product(
            gid, [self._graphql_variant(
                '%s-variant' % gid, sku=sku,
            )], updated_at=updated_at,
        ))
        job.invalidate_recordset()
        return job, first, second, sent

    def _ambiguous_variant_fixture(self, sku='DUP-VAR', name=None):
        """One Odoo template whose TWO variants both carry the same SKU.

        The shape matters, and getting it wrong is how a variant-ambiguity
        test can silently exercise template matching instead. `_resolve_
        variant_product` reaches `_match_variant_candidate` only when the
        template was resolved by CANDIDATE MATCH: an `existing_binding`
        template with attribute lines is routed to `_instantiate_refresh_
        variant` and never performs variant candidate search at all, and a
        `created_singleton` template takes the index-0 shortcut.

        So: exactly one Odoo template carries the incoming SKU (making
        template resolution unambiguous, `candidate_match`), and that
        template has two variants both carrying it (making VARIANT resolution
        ambiguous).
        """
        attribute = self.env['product.attribute'].create({
            'name': 'Match Size %s' % sku,
            'create_variant': 'always',
            'value_ids': [
                (0, 0, {'name': 'Match S'}),
                (0, 0, {'name': 'Match M'}),
            ],
        })
        template = self.env['product.template'].create({
            'name': name or 'Ambiguous Variant Parent %s' % sku,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            })],
        })
        variants = template.product_variant_ids
        self.assertEqual(len(variants), 2)
        variants.write({'default_code': sku})
        return template, variants

    def _ambiguous_variant_run(self, gid='gid://shopify/Product/8301',
                               updated_at=REMOTE_STAMP, sku='DUP-VAR'):
        template, variants = self._ambiguous_variant_fixture(sku=sku)
        job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid,
            [self._graphql_variant('%s-variant' % gid, sku=sku)],
            updated_at=updated_at,
        ))
        job.invalidate_recordset()
        return job, template, variants

    def _confirm(self, decision, chosen, user=None):
        user = user or self.roles['reviewer']
        wizard = self.Wizard.with_user(user).with_context(
            default_decision_id=decision.id,
        ).create({})
        field = (
            'selected_template_id'
            if decision.decision_level == DECISION_LEVEL_TEMPLATE
            else 'selected_variant_id'
        )
        wizard.write({field: chosen.id})
        return wizard.action_confirm()

    # ==================================================================
    # A. The dispatcher really reaches the importer, and an unambiguous
    #    import really writes what it says it writes.
    # ==================================================================

    def test_the_real_dispatcher_reaches_the_importer_and_binds(self):
        gid = 'gid://shopify/Product/8101'
        job = self._import_job(gid)
        sent = self._drain(self._graphql_product(
            gid, [self._graphql_variant(
                '%s-variant' % gid, sku='UNAMBIGUOUS-1',
            )], title='Unambiguous Product',
        ))
        job.invalidate_recordset()
        # Work was ADMITTED: the transport ran, and the job moved.
        self.assertTrue(sent, 'the importer never issued a Shopify read')
        self.assertEqual(job.state, 'succeeded')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.shopify_title, 'Unambiguous Product')
        self.assertEqual(binding.shopify_updated_at, REMOTE_STAMP)
        variant_binding = self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', '%s-variant' % gid),
        ])
        self.assertEqual(len(variant_binding), 1)
        self.assertEqual(
            variant_binding.product_template_binding_id, binding,
        )
        self.assertFalse(self.Decision.search([
            ('store_id', '=', self.store.id),
        ]), 'an unambiguous import must raise no decision at all')

    def test_zero_shopify_mutation_reaches_the_transport(self):
        gid = 'gid://shopify/Product/8102'
        self._import_job(gid)
        sent = self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='NO-MUT-1')],
        ))
        self.assertTrue(sent)
        for request in sent:
            query = (request.get('query') or '').lower()
            self.assertNotIn('mutation', query)
            self.assertTrue(query.strip().startswith('query'))

    # ==================================================================
    # B. The ambiguity persists a decision that survives the blocked-job
    #    transaction -- the whole point of the dispatcher seam.
    # ==================================================================

    def test_an_ambiguous_template_persists_a_durable_decision(self):
        job, first, second, sent = self._ambiguous_template_run()
        self.assertTrue(sent, 'the importer never ran')
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'ambiguous_match')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(
            len(decision), 1,
            'the decision did not survive the importer savepoint rollback',
        )
        self.assertEqual(decision.state, 'pending')
        self.assertEqual(decision.decision_level, DECISION_LEVEL_TEMPLATE)
        self.assertEqual(decision.store_id, self.store)
        self.assertEqual(decision.company_id, self.company)
        self.assertEqual(decision.remote_updated_at, REMOTE_STAMP)
        self.assertEqual(decision.job_payload_hash, job.payload_hash)
        self.assertEqual(decision.match_key, 'sku_reference')
        self.assertEqual(decision.sku_preview, 'DUP-TPL')
        self.assertEqual(decision.candidate_total, 2)
        self.assertEqual(
            set(decision.candidate_template_ids.ids), {first.id, second.id},
        )
        self.assertTrue(job.product_match_decision_pending)
        # And nothing was bound.
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/8201'),
        ]))

    def test_an_ambiguous_variant_persists_a_durable_decision(self):
        job, template, variants = self._ambiguous_variant_run()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'ambiguous_match')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.decision_level, DECISION_LEVEL_VARIANT)
        self.assertEqual(
            decision.shopify_variant_gid,
            'gid://shopify/Product/8301-variant',
        )
        self.assertEqual(decision.resolved_template_id, template)
        self.assertEqual(
            set(decision.candidate_variant_ids.ids), set(variants.ids),
        )
        self.assertEqual(decision.candidate_total, 2)

    def test_a_decision_written_inside_the_importer_savepoint_would_not_survive(self):
        """The load-bearing proof for the dispatcher seam's existence.

        This is not a test of the production path; it is the measurement that
        justifies it. A decision created where the ambiguity is FOUND -- i.e.
        inside `import_product_sync`'s savepoint, immediately before the raise
        -- is discarded by the same ROLLBACK TO SAVEPOINT that discards the
        partial product. If this ever stops being true, the seam can be
        simplified; while it is true, the seam is the only correct place.
        """
        self._make_product('Savepoint A', sku='SAVEPOINT-DUP')
        self._make_product('Savepoint B', sku='SAVEPOINT-DUP')
        gid = 'gid://shopify/Product/8250'
        job = self._import_job(gid)
        marker = 'v1:savepoint-probe'
        original = type(self.Importer)._resolve_template

        def resolve_inside_savepoint(importer_self, store, payload, settings,
                                     notes, dispatched_job=None):
            self.env['shopify.connector.product.match.decision'].sudo().create({
                'store_id': store.id,
                'job_id': job.id,
                'decision_level': DECISION_LEVEL_TEMPLATE,
                'shopify_product_gid': payload.get('gid'),
                'remote_updated_at': REMOTE_STAMP,
                'decision_key': marker,
                'match_key': 'sku_reference',
                'match_value_digests': json.dumps([
                    match_value_digest(self.env, 'SAVEPOINT-DUP'),
                ]),
            })
            return original(
                importer_self, store, payload, settings, notes, job,
            )

        with patch.object(
            type(self.Importer), '_resolve_template', resolve_inside_savepoint,
        ):
            self._drain(self._graphql_product(
                gid, [self._graphql_variant(
                    '%s-v' % gid, sku='SAVEPOINT-DUP',
                )],
            ))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(
            self.Decision.sudo().search([('decision_key', '=', marker)]),
            'a decision written inside the importer savepoint survived it -- '
            'if that is genuinely true now, the dispatcher seam can be '
            'simplified; until then it is the only durable place',
        )
        # The production seam still recorded its own, in the same run.
        self.assertTrue(self.Decision.search([('job_id', '=', job.id)]))

    def test_no_decision_is_recorded_without_a_provable_remote_identity(self):
        """Fail closed. A payload with no `updatedAt` cannot be pinned to a
        version, so a decision made against it could be consumed against a
        product that has since changed. The job still blocks; it offers no
        decision, and the generic route stays available."""
        self._make_product('No Stamp A', sku='NO-STAMP')
        self._make_product('No Stamp B', sku='NO-STAMP')
        gid = 'gid://shopify/Product/8260'
        job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='NO-STAMP')],
            updated_at=None,
        ))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertFalse(self.Decision.search([('job_id', '=', job.id)]))
        self.assertFalse(job.product_match_decision_pending)
        # ...and the generic route is NOT refused, because nothing better is
        # on offer.
        job.with_user(self.roles['reviewer']).action_resolve_manual_review()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    # ==================================================================
    # C. Generic resolution refuses while a decision is unresolved.
    # ==================================================================

    def test_generic_resolve_review_refuses_while_a_decision_is_pending(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        with self.assertRaises(UserError) as ctx:
            job.with_user(
                self.roles['reviewer']
            ).action_resolve_manual_review()
        self.assertIn('match decision', str(ctx.exception))
        job.invalidate_recordset()
        self.assertEqual(
            job.state, 'blocked_manual_review',
            'the refusal must leave the job exactly where it was',
        )

    def test_needs_attention_opens_the_product_match_decision(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        action = job.with_user(
            self.roles['reviewer']
        ).action_open_attention_case()
        self.assertEqual(
            action['res_model'],
            'shopify.connector.product.match.decision.wizard',
        )
        self.assertEqual(action['target'], 'new')

    def test_generic_resolve_review_is_allowed_once_the_decision_is_made(self):
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        job.invalidate_recordset()
        # The confirmation already re-queued it, so there is nothing left to
        # resolve -- which is the honest outcome, and is what the generic
        # route says.
        self.assertEqual(job.state, 'queued')
        with self.assertRaises(UserError):
            job.with_user(
                self.roles['reviewer']
            ).action_resolve_manual_review()

    # ==================================================================
    # D. Roles.
    # ==================================================================

    def test_an_operator_may_start_an_import_but_not_decide_a_match(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        # Starting work: allowed.
        self.store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        # Deciding a match: refused, on the server, with no side effect.
        with self.assertRaises(AccessError):
            job.with_user(
                self.roles['operator']
            ).action_open_product_match_decision()
        decision = self.Decision.search([('job_id', '=', job.id)])
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.roles['operator']).with_context(
                default_decision_id=decision.id,
            ).create({})
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')

    def test_an_auditor_may_not_decide_a_match(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        with self.assertRaises(AccessError):
            job.with_user(
                self.roles['auditor']
            ).action_open_product_match_decision()

    def test_a_reviewer_and_an_administrator_may_both_decide(self):
        for role, gid, sku in (
            ('reviewer', 'gid://shopify/Product/8401', 'ROLE-DUP-1'),
            ('admin', 'gid://shopify/Product/8402', 'ROLE-DUP-2'),
        ):
            job, first, _second, _sent = self._ambiguous_template_run(
                gid=gid, sku=sku,
            )
            decision = self.Decision.search([('job_id', '=', job.id)])
            self._confirm(decision, first, user=self.roles[role])
            decision.invalidate_recordset()
            self.assertEqual(decision.state, 'confirmed')
            self.assertEqual(decision.resolved_uid, self.roles[role])

    def test_the_durable_decision_is_read_only_over_rpc_for_every_role(self):
        """Least privilege, asserted rather than assumed. Every connector role
        may READ a decision; none may write, create or delete one. Every write
        in production goes through the revalidated service paths."""
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        for label in ('auditor', 'operator', 'reviewer', 'admin'):
            scoped = decision.with_user(self.roles[label])
            self.assertTrue(scoped.read(['state']))
            with self.assertRaises(AccessError, msg=label):
                scoped.write({'state': 'confirmed'})
            with self.assertRaises(AccessError, msg=label):
                scoped.unlink()
            with self.assertRaises(AccessError, msg=label):
                self.Decision.with_user(self.roles[label]).create({
                    'store_id': self.store.id,
                    'job_id': job.id,
                    'decision_level': DECISION_LEVEL_TEMPLATE,
                    'shopify_product_gid': 'gid://shopify/Product/forged',
                    'remote_updated_at': REMOTE_STAMP,
                    'decision_key': 'v1:forged',
                    'match_key': 'sku_reference',
                })

    # ==================================================================
    # E. Multi-company and multi-store isolation.
    # ==================================================================

    def test_a_foreign_company_administrator_sees_no_decision_at_all(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertTrue(decision)
        visible = self.Decision.with_user(self.foreign_admin).search([])
        self.assertNotIn(
            decision.id, visible.ids,
            'the fail-closed company rule did not hide the decision',
        )
        self.assertEqual(
            self.Decision.with_user(self.foreign_admin).search_count([]), 0,
            'a count is disclosure too -- it proves the record exists',
        )
        with self.assertRaises(AccessError):
            decision.with_user(self.foreign_admin).read(['sku_preview'])

    def test_a_foreign_company_administrator_cannot_decide(self):
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.foreign_admin).with_context(
                default_decision_id=decision.id,
            ).create({})
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')

    def test_candidates_never_include_a_foreign_company_record(self):
        """A same-SKU product owned by another company is not a candidate.

        Read as the connector's own rule rather than as a side effect of
        Odoo's product rules: the eligible set filters on the STORE's company
        explicitly, so it holds even for a user who has both companies active
        and would therefore be shown the foreign product by `product.product`'s
        own record rule.
        """
        self._make_product('Cross A', sku='CROSS-DUP')
        self._make_product(
            'Cross Foreign', sku='CROSS-DUP', company=self.other_company,
        )
        gid = 'gid://shopify/Product/8501'
        job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='CROSS-DUP')],
        ))
        job.invalidate_recordset()
        # Two records carry the SKU, so the importer stopped...
        self.assertEqual(job.state, 'blocked_manual_review')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertTrue(decision)
        # ...but only the same-company one is a candidate a human may pick.
        self.roles['admin'].write({
            'company_ids': [(6, 0, [self.company.id, self.other_company.id])],
        })
        eligible = decision.with_user(self.roles['admin']).with_context(
            allowed_company_ids=[self.company.id, self.other_company.id],
        ).eligible_candidates()
        self.assertTrue(eligible)
        for template in eligible:
            self.assertIn(
                template.company_id, (self.env['res.company'], self.company),
            )
        self.assertNotIn(
            'Cross Foreign', eligible.mapped('name'),
        )

    def test_a_decision_cannot_select_a_foreign_company_record(self):
        """Odoo's own `_check_company`, opted into on the model, is the
        write-side authority -- and it holds under `sudo()`."""
        job, _first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        foreign, _variant = self._make_product(
            'Foreign Selection', sku='FOREIGN-SEL', company=self.other_company,
        )
        # Odoo 19 raises `UserError` from `_check_company`
        # (`odoo/orm/models.py::_check_company` at the pin), not a
        # ValidationError -- asserted as the exact class the ORM really
        # raises rather than the one the name suggests.
        with self.assertRaises(UserError):
            decision.sudo().write({'selected_template_id': foreign.id})

    def test_two_stores_do_not_see_one_another_decisions(self):
        job_a, first, _second, _sent = self._ambiguous_template_run()
        # A second store in the SAME company, so the company rule is not what
        # separates them -- the store scoping is.
        second_store = self._make_store(
            'Match Decision Sibling', 'match-decision-sibling', self.company,
        )
        self._make_product('Sibling A', sku='SIB-DUP')
        self._make_product('Sibling B', sku='SIB-DUP')
        gid = 'gid://shopify/Product/8601'
        job_b = self._import_job(gid, store=second_store)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='SIB-DUP')],
        ))
        job_b.invalidate_recordset()
        decision_a = self.Decision.search([('job_id', '=', job_a.id)])
        decision_b = self.Decision.search([('job_id', '=', job_b.id)])
        self.assertTrue(decision_a and decision_b)
        self.assertNotEqual(decision_a, decision_b)
        self.assertEqual(decision_a.store_id, self.store)
        self.assertEqual(decision_b.store_id, second_store)
        # Confirming one resumes ONLY its own job.
        self._confirm(decision_a, first)
        job_a.invalidate_recordset()
        job_b.invalidate_recordset()
        self.assertEqual(job_a.state, 'queued')
        self.assertEqual(job_b.state, 'blocked_manual_review')

    # ==================================================================
    # F. Confirmation: revalidation, refusals, and the resume.
    # ==================================================================

    def test_one_confirmed_decision_resumes_the_exact_source_job_once(self):
        job, first, _second, _sent = self._ambiguous_template_run()
        other_job = self._import_job('gid://shopify/Product/8199')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        self.assertEqual(job.retry_count, 0)
        self.assertFalse(job.manual_review_subreason)
        self.assertEqual(decision.state, 'confirmed')
        self.assertEqual(decision.selected_template_id, first)
        self.assertEqual(decision.resolved_uid, self.roles['reviewer'])
        self.assertTrue(decision.resolved_at)
        self.assertEqual(decision.resumed_job_state, 'queued')
        # No OTHER job was touched.
        other_job.invalidate_recordset()
        self.assertEqual(other_job.state, 'queued')

    def test_a_second_confirmation_of_the_same_decision_refuses(self):
        job, first, second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard_one = self.Wizard.with_user(
            self.roles['reviewer']
        ).with_context(default_decision_id=decision.id).create({})
        wizard_two = self.Wizard.with_user(
            self.roles['admin']
        ).with_context(default_decision_id=decision.id).create({})
        wizard_one.write({'selected_template_id': first.id})
        wizard_one.action_confirm()
        wizard_two.write({'selected_template_id': second.id})
        with self.assertRaises(UserError) as ctx:
            wizard_two.action_confirm()
        self.assertIn('already been made', str(ctx.exception))
        decision.invalidate_recordset()
        self.assertEqual(
            decision.selected_template_id, first,
            'the loser overwrote the winner',
        )

    def test_a_decision_whose_job_moved_on_refuses(self):
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': first.id})
        # Somebody cancels the job while the dialog is open.
        job.with_user(self.roles['admin']).sudo().write({
            'state': 'cancelled', 'manual_review_subreason': False,
            'cancel_reason': 'operator changed their mind',
        })
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm()
        self.assertIn('no longer blocked', str(ctx.exception))
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')

    def test_a_stale_payload_identity_refuses(self):
        """§8.2.9: the remote/payload identity must be unchanged at confirm."""
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': first.id})
        job.sudo().write({'payload_hash': 'a-different-remote-version'})
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm()
        self.assertIn('changed', str(ctx.exception))
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')

    def test_an_ineligible_candidate_refuses(self):
        """A candidate that stopped carrying the identifier is not a choice."""
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': first.id})
        first.product_variant_ids.write({'default_code': 'CHANGED-SKU'})
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm()
        self.assertIn('no longer an eligible match', str(ctx.exception))

    def test_a_candidate_bound_meanwhile_refuses(self):
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': first.id})
        # A concurrent import binds that very product to this store.
        self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/other-8201',
            'product_template_id': first.id,
            'match_key': 'manual',
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_a_foreign_decision_id_forged_into_the_context_refuses(self):
        """A reviewer of one company cannot reach another company's decision
        by naming its id -- the wizard checks the CALLER's access, not its
        own."""
        job, _first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        with self.assertRaises(AccessError):
            self.Wizard.with_user(self.foreign_admin).with_context(
                default_decision_id=decision.id,
            ).create({})

    def test_an_empty_choice_refuses(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision.id,
        ).create({})
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_a_competing_decision_on_the_same_odoo_record_refuses(self):
        """One Odoo record can stand for only one Shopify product."""
        job_a, first, _second, _sent = self._ambiguous_template_run(
            gid='gid://shopify/Product/8701', sku='COMPETE-DUP',
        )
        decision_a = self.Decision.search([('job_id', '=', job_a.id)])
        self._confirm(decision_a, first)
        # A second Shopify product, ambiguous over the SAME two Odoo records.
        job_b = self._import_job('gid://shopify/Product/8702')
        self._drain(self._graphql_product(
            'gid://shopify/Product/8702',
            [self._graphql_variant(
                'gid://shopify/Product/8702-v', sku='COMPETE-DUP',
            )],
        ))
        job_b.invalidate_recordset()
        decision_b = self.Decision.search([('job_id', '=', job_b.id)])
        self.assertTrue(decision_b)
        wizard = self.Wizard.with_user(self.roles['reviewer']).with_context(
            default_decision_id=decision_b.id,
        ).create({'selected_template_id': first.id})
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm()
        self.assertIn('already been matched', str(ctx.exception))

    # ==================================================================
    # G. Consumption: only the exact remote identity, and the binding.
    # ==================================================================

    def test_a_confirmed_decision_is_consumed_and_binds_with_the_actor(self):
        gid = 'gid://shopify/Product/8801'
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='CONSUME-DUP',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        # The resumed job is re-drained against the SAME remote version.
        sent = self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='CONSUME-DUP')],
        ))
        self.assertTrue(sent)
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.product_template_id, first)
        self.assertEqual(binding.match_key, 'manual')
        self.assertEqual(binding.matched_by_uid, self.roles['reviewer'])
        self.assertEqual(decision.state, 'consumed')
        self.assertEqual(decision.resulting_template_binding_id, binding)
        self.assertTrue(decision.consumed_at)

    def test_a_confirmed_variant_decision_is_consumed_and_binds(self):
        gid = 'gid://shopify/Product/8302'
        job, template, variants = self._ambiguous_variant_run(
            gid=gid, sku='DUP-VAR-CONSUME',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        chosen = variants[0]
        self._confirm(decision, chosen)
        self._drain(self._graphql_product(
            gid,
            [self._graphql_variant(
                '%s-variant' % gid, sku='DUP-VAR-CONSUME',
            )],
        ))
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        variant_binding = self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', '%s-variant' % gid),
        ])
        self.assertEqual(len(variant_binding), 1)
        self.assertEqual(variant_binding.product_variant_id, chosen)
        self.assertEqual(variant_binding.match_key, 'manual')
        self.assertEqual(
            variant_binding.matched_by_uid, self.roles['reviewer'],
        )
        self.assertEqual(
            variant_binding.product_template_binding_id.product_template_id,
            template,
        )
        self.assertEqual(decision.state, 'consumed')
        self.assertEqual(decision.resulting_variant_binding_id, variant_binding)

    def test_the_importer_consumes_only_the_matching_remote_identity(self):
        """§8.2.11. The merchant edits the product on Shopify between the
        decision and the resume. The decision describes the OLD version, so
        it is not applied: the import stops again and asks about the new one.
        """
        gid = 'gid://shopify/Product/8901'
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='IDENTITY-DUP',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        # The resumed import now sees a DIFFERENT `updatedAt`.
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='IDENTITY-DUP')],
            updated_at=LATER_STAMP,
        ))
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(
            job.state, 'blocked_manual_review',
            'a stale decision was applied to a changed remote product',
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ]))
        # The old decision is superseded and says why; a fresh one is pending.
        self.assertEqual(decision.state, 'superseded')
        self.assertTrue(decision.superseded_reason)
        fresh = self.Decision.search([
            ('store_id', '=', self.store.id),
            ('shopify_product_gid', '=', gid),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh.remote_updated_at, LATER_STAMP)
        self.assertNotEqual(fresh, decision)

    def test_a_decision_for_another_store_is_never_consumed(self):
        """The lookup is store-scoped, so an identical Shopify product
        imported by two stores never borrows the other store's decision."""
        gid = 'gid://shopify/Product/8951'
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='FOREIGN-CONSUME',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        sibling = self._make_store(
            'Match Decision Consume Sibling', 'match-decision-consume',
            self.company,
        )
        sibling_job = self._import_job(gid, store=sibling)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='FOREIGN-CONSUME')],
        ))
        sibling_job.invalidate_recordset()
        self.assertEqual(
            sibling_job.state, 'blocked_manual_review',
            "one store's decision was consumed by another store's import",
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', sibling.id), ('shopify_gid', '=', gid),
        ]))

    def test_a_decision_selecting_a_candidate_that_vanished_is_not_consumed(self):
        """Confirmed is not a licence. The importer recomputes candidates and
        refuses a chosen record that is no longer among them."""
        gid = 'gid://shopify/Product/8971'
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='VANISH-DUP',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        first.product_variant_ids.write({'default_code': 'VANISHED'})
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='VANISH-DUP')],
        ))
        job.invalidate_recordset()
        # Only one candidate is left, so the import no longer needs a decision
        # at all -- it matches unambiguously, on the RIGHT record.
        self.assertEqual(job.state, 'succeeded')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(len(binding), 1)
        self.assertNotEqual(binding.product_template_id, first)
        self.assertEqual(binding.match_key, 'sku_reference')
        decision.invalidate_recordset()
        self.assertEqual(
            decision.state, 'confirmed',
            'an unconsumed decision must not silently claim it was applied',
        )

    def test_bindings_stay_unique_and_store_company_correct(self):
        gid = 'gid://shopify/Product/8991'
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='UNIQUE-DUP',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='UNIQUE-DUP')],
        ))
        # Re-import the very same product: the existing binding resolves it,
        # and no second binding appears.
        second_job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='UNIQUE-DUP')],
        ))
        second_job.invalidate_recordset()
        bindings = self.TemplateBinding.search([
            ('store_id', '=', self.store.id), ('shopify_gid', '=', gid),
        ])
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings.company_id, self.company)
        self.assertEqual(bindings.store_id, self.store)
        variant_bindings = self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', '%s-v' % gid),
        ])
        self.assertEqual(len(variant_bindings), 1)
        self.assertEqual(variant_bindings.company_id, self.company)

    def test_an_unresolved_ambiguity_cannot_loop(self):
        """§9 K-P0. Re-queueing without a decision reproduces the block, and
        the decision row does not multiply."""
        gid = 'gid://shopify/Product/8999'
        job, _first, _second, _sent = self._ambiguous_template_run(
            gid=gid, sku='LOOP-DUP',
        )
        first_decision = self.Decision.search([('job_id', '=', job.id)])
        job.with_user(self.roles['admin']).sudo().write({
            'state': 'queued', 'manual_review_subreason': False,
            'finished_at': False,
        })
        self._drain(self._graphql_product(
            gid, [self._graphql_variant('%s-v' % gid, sku='LOOP-DUP')],
        ))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        decisions = self.Decision.search([
            ('store_id', '=', self.store.id),
            ('shopify_product_gid', '=', gid),
        ])
        self.assertEqual(
            len(decisions), 1,
            'the same ambiguity must coalesce onto one decision row',
        )
        self.assertEqual(decisions, first_decision)
        self.assertEqual(decisions.state, 'pending')

    # ==================================================================
    # H. Evidence hygiene: bounded, sanitized, schema-exact.
    # ==================================================================

    def test_evidence_is_bounded_and_scrubbed(self):
        long_title = 'A' * 500
        evidence = build_match_evidence(
            self.env,
            level=DECISION_LEVEL_TEMPLATE,
            shopify_product_gid='gid://shopify/Product/1',
            remote_updated_at=REMOTE_STAMP,
            match_key='sku_reference',
            match_values=['B' * 500] + ['S%d' % i for i in range(50)],
            candidate_ids=list(range(1, 60)),
            candidate_total=59,
            title_preview=long_title,
        )
        parsed = parse_match_evidence(evidence)
        self.assertTrue(parsed)
        self.assertEqual(len(parsed['title_preview']), MATCH_TITLE_MAX_LEN)
        # Every match value is carried as a FIXED-LENGTH keyed digest, so the
        # payload is bounded by construction rather than by truncating the
        # merchant's identifiers -- and none of them appears in it.
        self.assertLessEqual(len(parsed['match_value_digests']),
                             MATCH_VALUES_LIMIT)
        self.assertTrue(all(
            len(value) == MATCH_DIGEST_LEN
            for value in parsed['match_value_digests']
        ))
        self.assertNotIn('B' * 500, evidence)
        self.assertNotIn('S1', evidence)
        self.assertLessEqual(len(parsed['candidate_ids']),
                             MATCH_CANDIDATE_LIMIT)
        self.assertEqual(parsed['candidate_total'], 59)

    def test_no_secret_or_pii_reaches_the_evidence(self):
        self.assertNotIn('shpat_', safe_match_preview(
            'token %s here' % DUMMY_TOKEN, 200,
        ))
        self.assertIn('[redacted-email]', safe_match_preview(
            'ships to buyer@example.com', 200,
        ))
        self.assertIn('[redacted-phone]', safe_match_preview(
            'call +1 555 123 4567', 200,
        ))

    def test_a_stored_decision_carries_no_secret(self):
        job, _first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        rendered = json.dumps(decision.sudo().read()[0], default=str)
        self.assertNotIn('shpat_', rendered)
        self.assertNotIn(DUMMY_TOKEN, rendered)

    def test_malformed_evidence_is_never_a_decision(self):
        good = json.loads(build_match_evidence(
            self.env,
            level=DECISION_LEVEL_TEMPLATE,
            shopify_product_gid='gid://shopify/Product/1',
            remote_updated_at=REMOTE_STAMP,
            match_key='sku_reference', match_values=['S1'],
            candidate_ids=[1, 2], candidate_total=2,
        ))
        self.assertTrue(parse_match_evidence(json.dumps(good)))
        for mutate in (
            lambda p: p.update({'schema': 'something.else'}),
            lambda p: p.update({'level': 'neither'}),
            lambda p: p.update({'match_key': 'name'}),
            lambda p: p.update({'match_value_digests': []}),
            lambda p: p.update({'match_value_digests': ['not-a-digest']}),
            lambda p: p.update({'shopify_product_gid': 'bad\x00gid'}),
            lambda p: p.update({'remote_updated_at': ''}),
            lambda p: p.update({'candidate_ids': ['1']}),
            lambda p: p.update({'extra_key': 1}),
            lambda p: p.pop('title_preview'),
        ):
            payload = dict(good)
            mutate(payload)
            self.assertIsNone(
                parse_match_evidence(json.dumps(payload)),
                'a malformed payload validated: %r' % (payload,),
            )
        self.assertIsNone(parse_match_evidence('not json'))
        self.assertIsNone(parse_match_evidence(''))
        self.assertIsNone(parse_match_evidence(None))

    def test_identity_is_read_from_the_payload_not_from_the_sentence(self):
        """Reword the human message; nothing about the decision changes."""
        gid = 'gid://shopify/Product/9101'
        self._make_product('Wording A', sku='WORDING-DUP')
        self._make_product('Wording B', sku='WORDING-DUP')
        job = self._import_job(gid)
        original = type(self.Importer)._resolve_template

        def reworded(importer_self, store, payload, settings, notes,
                     job=None):
            try:
                return original(
                    importer_self, store, payload, settings, notes, job,
                )
            except JobHandlerError as exc:
                if exc.error_class != 'ambiguous_match':
                    raise
                raise JobHandlerError(
                    exc.error_class,
                    'Completely different wording, in another language even.',
                    exc.technical_detail,
                ) from None

        with patch.object(type(self.Importer), '_resolve_template', reworded):
            self._drain(self._graphql_product(
                gid, [self._graphql_variant('%s-v' % gid, sku='WORDING-DUP')],
            ))
        job.invalidate_recordset()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.shopify_product_gid, gid)
        self.assertEqual(decision.remote_updated_at, REMOTE_STAMP)
        self.assertEqual(decision.candidate_total, 2)

    def test_the_evidence_schema_is_exact_not_a_minimum(self):
        self.assertEqual(
            set(json.loads(build_match_evidence(
                self.env,
                level=DECISION_LEVEL_TEMPLATE,
                shopify_product_gid='gid://shopify/Product/1',
                remote_updated_at=REMOTE_STAMP,
                match_key='barcode', match_values=['B1'],
                candidate_ids=[1, 2], candidate_total=2,
            ))),
            set(MATCH_EVIDENCE_KEYS),
        )

    def test_the_decision_key_cannot_collide_across_components(self):
        """Length-prefixed, so no shuffling of component boundaries collides."""
        self.assertNotEqual(
            decision_key_for('template', 'ab', 'c', REMOTE_STAMP),
            decision_key_for('template', 'a', 'bc', REMOTE_STAMP),
        )
        self.assertEqual(
            decision_key_for('template', 'ab', 'c', REMOTE_STAMP),
            decision_key_for('template', 'ab', 'c', REMOTE_STAMP),
        )

    # ==================================================================
    # I. Untouched neighbours.
    # ==================================================================

    def test_attribute_conflict_mode_still_governs_structure_conflicts(self):
        """§8.2.17: nothing here reinterprets an attribute-structure conflict
        as an ambiguous match. It stays a `binding_conflict` governed by
        `product_import_attribute_conflict_mode`."""
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', self.store.id)], limit=1,
        )
        self.assertIn(
            'product_import_attribute_conflict_mode', settings._fields,
        )
        source = (
            self.env['shopify.connector.product.importer']
            ._match_variant_candidate.__doc__ or ''
        )
        self.assertNotIn('attribute', source.lower())

    def test_the_decision_model_makes_no_binding_field_editable(self):
        """The protected binding surface is unchanged by this batch."""
        job, first, _second, _sent = self._ambiguous_template_run()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/protected-check',
            'product_template_id': first.id,
            'match_key': 'manual',
        })
        with self.assertRaises(AccessError):
            binding.with_user(self.roles['admin']).write({
                'product_template_id': first.id,
            })

    # ==================================================================
    # J. THE BATCH 2 CORRECTION (F1/F2/F3): identity is opaque, display is
    #    sanitized, and exact matching survives both.
    #
    #    EVERY TEST IN THIS SECTION USES PRODUCTION-SHAPED DATA, AND THAT
    #    IS THE POINT. The pre-correction suite used `gid://shopify/
    #    Product/8201` and `DUP-TPL`. A four-digit suffix and an alphabetic
    #    SKU are the two shapes `safe_match_preview`'s phone pattern does
    #    NOT rewrite (it needs a leading digit, six or more digit/separator
    #    characters, and a trailing digit), so a green suite proved the
    #    route worked for identities no Shopify store issues. Real GIDs
    #    carry a 13-to-14-digit suffix; real SKUs and barcodes are
    #    routinely all digits. Those are the values below.
    # ==================================================================

    # Shapes a real store actually produces.
    REAL_PRODUCT_GID = 'gid://shopify/Product/7346299043911'
    REAL_PRODUCT_GID_2 = 'gid://shopify/Product/9876543210987'
    REAL_VARIANT_GID = 'gid://shopify/ProductVariant/45123456789012'
    NUMERIC_SKU = '1234567890123'
    HYPHENATED_NUMERIC_SKU = '012-345-6789'
    EAN13_BARCODE = '4006381333931'

    def test_the_display_scrubber_really_does_rewrite_every_real_shape(self):
        """The measurement the whole section rests on.

        If this ever stops being true, `safe_match_preview` has changed and
        the separation below can be re-examined. While it IS true, using it
        on an identity destroys the identity.
        """
        for shape in (
            self.REAL_PRODUCT_GID, self.REAL_PRODUCT_GID_2,
            self.REAL_VARIANT_GID, self.NUMERIC_SKU,
            self.HYPHENATED_NUMERIC_SKU, self.EAN13_BARCODE,
        ):
            self.assertNotEqual(
                safe_match_preview(shape, 200), shape,
                '%r survives the display scrubber, so it is not a shape that '
                'demonstrates the defect' % (shape,),
            )
        # ...and the two shapes the old fixtures used do NOT, which is why
        # the old suite was green against the defect.
        for survivor in ('gid://shopify/Product/8201', 'DUP-TPL'):
            self.assertEqual(safe_match_preview(survivor, 200), survivor)

    def test_a_real_product_gid_is_stored_and_keyed_exactly(self):
        """§10.1/§10.8. Identity in, identity out, byte for byte."""
        job, first, second, sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        self.assertTrue(sent, 'the importer never ran')
        self.assertEqual(job.state, 'blocked_manual_review')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.shopify_product_gid, self.REAL_PRODUCT_GID)
        self.assertEqual(decision.remote_updated_at, REMOTE_STAMP)
        # The durable key is the one the raw payload reproduces.
        self.assertEqual(
            decision.decision_key,
            decision_key_for(
                DECISION_LEVEL_TEMPLATE, self.REAL_PRODUCT_GID, '',
                REMOTE_STAMP,
            ),
        )
        # And that is exactly what consumption looks for.
        self.assertEqual(
            self.Decision._confirmed_for(
                self.store, DECISION_LEVEL_TEMPLATE, self.REAL_PRODUCT_GID,
                '', REMOTE_STAMP,
            ),
            self.Decision.browse(),
            'nothing is confirmed yet',
        )
        self._confirm(decision, first)
        decision.invalidate_recordset()
        self.assertEqual(
            self.Decision._confirmed_for(
                self.store, DECISION_LEVEL_TEMPLATE, self.REAL_PRODUCT_GID,
                '', REMOTE_STAMP,
            ),
            decision,
            'the key computed from the RAW payload must find the decision '
            'the raw payload produced',
        )
        self.assertTrue(second)

    def test_a_real_variant_gid_is_stored_and_keyed_exactly(self):
        """§10.2, at the variant level."""
        gid = self.REAL_PRODUCT_GID
        variant_gid = self.REAL_VARIANT_GID
        template, variants = self._ambiguous_variant_fixture(
            sku=self.NUMERIC_SKU,
        )
        job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid,
            [self._graphql_variant(variant_gid, sku=self.NUMERIC_SKU)],
        ))
        job.invalidate_recordset()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.decision_level, DECISION_LEVEL_VARIANT)
        self.assertEqual(decision.shopify_product_gid, gid)
        self.assertEqual(decision.shopify_variant_gid, variant_gid)
        self.assertEqual(
            decision.decision_key,
            decision_key_for(
                DECISION_LEVEL_VARIANT, gid, variant_gid, REMOTE_STAMP,
            ),
        )
        self.assertEqual(decision.resolved_template_id, template)
        self.assertEqual(
            set(decision.candidate_variant_ids.ids), set(variants.ids),
        )

    def test_two_real_products_sharing_an_updated_at_stay_two_decisions(self):
        """§10.3/§10.15, and the sharpest form of the identity defect.

        Both GIDs end in a long digit run, so the display scrubber collapses
        both to `gid://shopify/Product/[redacted-phone]`. With the same
        `updatedAt` they produced ONE key -- so the second product's failure
        found the first product's pending decision, re-pointed it at the
        second product's job, and a reviewer deciding about product A
        resumed the import of product B.
        """
        self.assertEqual(
            safe_match_preview(self.REAL_PRODUCT_GID, 200),
            safe_match_preview(self.REAL_PRODUCT_GID_2, 200),
            'the two GIDs must be indistinguishable AFTER sanitization for '
            'this test to be about the defect',
        )
        first_job, first_a, _first_b, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        second_job, second_a, _second_b, _sent2 = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID_2, sku=self.HYPHENATED_NUMERIC_SKU,
        )
        first = self.Decision.search([('job_id', '=', first_job.id)])
        second = self.Decision.search([('job_id', '=', second_job.id)])
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first.decision_key, second.decision_key)
        self.assertEqual(first.remote_updated_at, second.remote_updated_at)
        # Neither was re-pointed: each decision still belongs to its own job,
        # and each job still has exactly one.
        self.assertEqual(first.job_id, first_job)
        self.assertEqual(second.job_id, second_job)
        self.assertEqual(first.state, 'pending')
        self.assertEqual(second.state, 'pending')
        # Deciding one resumes ONE job and leaves the other exactly alone.
        self._confirm(first, first_a)
        first_job.invalidate_recordset()
        second_job.invalidate_recordset()
        second.invalidate_recordset()
        self.assertEqual(first_job.state, 'queued')
        self.assertEqual(second_job.state, 'blocked_manual_review')
        self.assertEqual(second.state, 'pending')
        self.assertTrue(second_a)

    def test_a_numeric_sku_still_finds_its_candidates(self):
        """§10.4/§10.10. The eligible set is the reviewer's whole dialog.

        Under the defect the stored match value was the literal string
        `[redacted-phone]`, and `eligible_candidates()` searched
        `default_code in ['[redacted-phone]']` -- which no Odoo record
        carries. The reviewer was asked to choose from an empty list.
        """
        job, first, second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        eligible = decision.eligible_candidates()
        self.assertEqual(set(eligible.ids), {first.id, second.id})

    def test_a_hyphenated_numeric_sku_still_finds_its_candidates(self):
        """§10.5. Same shape, with separators the scrubber also swallows."""
        job, first, second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.HYPHENATED_NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(decision.match_key, 'sku_reference')
        self.assertEqual(
            set(decision.eligible_candidates().ids), {first.id, second.id},
        )

    def test_an_ean13_barcode_ambiguity_matches_and_stays_company_scoped(self):
        """§10.6, within what Odoo's own uniqueness rules actually permit.

        Odoo 19 enforces barcode uniqueness WITHIN a company
        (`product.product._check_barcode_uniqueness`, pin `30bde9ff`), so two
        same-company products cannot share an EAN-13 and a same-company
        barcode ambiguity is not a state the database can hold. Two products
        in DIFFERENT companies can, and `_find_template_candidates` searches
        with no company filter -- so this is the real, reachable barcode
        ambiguity, and it is also the one where company scoping matters most.
        """
        mine, _mine_variant = self._make_product(
            'EAN mine', barcode=self.EAN13_BARCODE, company=self.company,
        )
        theirs, _theirs_variant = self._make_product(
            'EAN theirs', barcode=self.EAN13_BARCODE,
            company=self.other_company,
        )
        gid = self.REAL_PRODUCT_GID
        job = self._import_job(gid)
        sent = self._drain(self._graphql_product(
            gid,
            [self._graphql_variant(
                self.REAL_VARIANT_GID, barcode=self.EAN13_BARCODE,
            )],
        ))
        job.invalidate_recordset()
        self.assertTrue(sent)
        self.assertEqual(job.state, 'blocked_manual_review')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        self.assertEqual(decision.match_key, 'barcode')
        self.assertEqual(decision.candidate_total, 2)
        # The snapshot already dropped the foreign-company candidate...
        self.assertEqual(set(decision.candidate_template_ids.ids), {mine.id})
        # ...and the digest comparison confirms the surviving one really does
        # carry the barcode Shopify sent.
        self.assertEqual(set(decision.eligible_candidates().ids), {mine.id})
        self.assertTrue(theirs)
        # And the whole route completes on it.
        self._confirm(decision, mine)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    def test_the_display_preview_stays_sanitized_while_identity_does_not(self):
        """§10.7. The two treatments, on the same record, at the same time."""
        job, _first, _second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(decision.sku_preview, '[redacted-phone]')
        self.assertEqual(decision.shopify_product_gid, self.REAL_PRODUCT_GID)

    def test_no_raw_identifier_reaches_a_log_a_payload_or_a_ui_field(self):
        """§10.9. The exact match value is nowhere a human or a DOM can read.

        The identifier is carried as a keyed digest, so the durable evidence,
        the job-log rows the dispatcher wrote, the exception text and every
        readable field of the decision can all be searched for it directly.
        """
        job, _first, _second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        logs = self.env['shopify.connector.job.log'].sudo().search(
            [('job_id', '=', job.id)],
        )
        self.assertTrue(logs, 'the dispatcher wrote no log to inspect')
        haystacks = [
            json.dumps(logs.read(), default=str),
            json.dumps(decision.sudo().read(), default=str),
            decision.match_value_digests or '',
            json.dumps(job.sudo().read(), default=str),
        ]
        for haystack in haystacks:
            self.assertNotIn(self.NUMERIC_SKU, haystack)
        # The digest IS there, and it is the thing that does the matching.
        self.assertIn(
            match_value_digest(self.env, self.NUMERIC_SKU),
            decision.match_value_digests,
        )

    def test_a_forged_candidate_id_is_refused_on_its_live_identifier(self):
        """§10.11. Same company is not enough, and never was.

        `candidate_ids` arrives on an exception payload. The persistence step
        drops foreign-company ids, but a SAME-company id costs an attacker or
        a bug nothing -- so eligibility is decided by recomputing the live
        record's identifier digest, not by membership of the payload's list.
        """
        job, first, second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        innocent, _variant = self._make_product(
            'Never carried the identifier', sku='SOMETHING-ELSE-ENTIRELY',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        # Forge it straight into the stored snapshot, which is the strongest
        # form of the attack: it is already past every parse-time check.
        decision.sudo().write({
            'candidate_template_ids': [(4, innocent.id)],
        })
        decision.invalidate_recordset()
        self.assertIn(innocent.id, decision.candidate_template_ids.ids)
        self.assertEqual(
            set(decision.eligible_candidates().ids), {first.id, second.id},
            'a same-company record that never carried the identifier was '
            'offered as an eligible match',
        )
        with self.assertRaises(UserError):
            self._confirm(decision, innocent)
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')

    def test_the_whole_template_route_completes_on_production_shaped_data(self):
        """§10.12. Dispatcher -> importer -> block -> decide -> resume ->
        consume -> binding, with nothing in it a real store would not send."""
        job, first, second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(decision.state, 'confirmed')
        self.assertEqual(decision.selected_template_id, first)
        self.assertEqual(job.state, 'queued')
        # The resumed import runs for real and consumes the decision.
        sent = self._drain(self._graphql_product(
            self.REAL_PRODUCT_GID,
            [self._graphql_variant(
                self.REAL_VARIANT_GID, sku=self.NUMERIC_SKU,
            )],
        ))
        self.assertTrue(sent, 'the resumed import never issued a read')
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(decision.state, 'consumed')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', self.REAL_PRODUCT_GID),
        ])
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.product_template_id, first)
        self.assertEqual(binding.match_key, 'manual')
        self.assertEqual(decision.resulting_template_binding_id, binding)
        self.assertNotEqual(binding.product_template_id, second)

    def test_the_whole_variant_route_completes_on_production_shaped_data(self):
        """§10.13, the variant equivalent, end to end."""
        gid = self.REAL_PRODUCT_GID_2
        variant_gid = self.REAL_VARIANT_GID
        template, variants = self._ambiguous_variant_fixture(
            sku=self.NUMERIC_SKU,
        )
        job = self._import_job(gid)
        self._drain(self._graphql_product(
            gid, [self._graphql_variant(variant_gid, sku=self.NUMERIC_SKU)],
        ))
        job.invalidate_recordset()
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        chosen = variants[0]
        self.assertIn(chosen.id, decision.eligible_candidates().ids)
        self._confirm(decision, chosen)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        sent = self._drain(self._graphql_product(
            gid, [self._graphql_variant(variant_gid, sku=self.NUMERIC_SKU)],
        ))
        self.assertTrue(sent)
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(decision.state, 'consumed')
        variant_binding = self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', variant_gid),
        ])
        self.assertEqual(len(variant_binding), 1)
        self.assertEqual(variant_binding.product_variant_id, chosen)
        self.assertEqual(
            decision.resulting_variant_binding_id, variant_binding,
        )
        self.assertEqual(variant_binding.product_variant_id.product_tmpl_id,
                         template)

    def test_a_changed_updated_at_refuses_the_confirmed_decision(self):
        """§10.14, on production-shaped identity.

        The product moved on Shopify after the decision was made, so the
        decision describes something that is no longer what would be
        imported. It is not consumed, and a fresh ambiguity is raised.
        """
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self._confirm(decision, first)
        # The merchant edits the product; the payload now carries a new stamp.
        self._drain(self._graphql_product(
            self.REAL_PRODUCT_GID,
            [self._graphql_variant(
                self.REAL_VARIANT_GID, sku=self.NUMERIC_SKU,
            )],
            updated_at=LATER_STAMP,
        ))
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            decision.state, 'superseded',
            'the decision for the OLD remote version must be retired, not '
            'applied to the new one',
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', self.REAL_PRODUCT_GID),
        ]))
        fresh = self.Decision.search([
            ('store_id', '=', self.store.id),
            ('shopify_product_gid', '=', self.REAL_PRODUCT_GID),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh.remote_updated_at, LATER_STAMP)

    def test_supersession_never_reaches_an_unrelated_product(self):
        """§10.15 again, from the supersession side.

        Under the defect `shopify_product_gid` was
        `gid://shopify/Product/[redacted-phone]` for every product with a long
        numeric suffix, so recording ONE new ambiguity superseded every other
        merchant decision in the store that happened to share that shape.
        """
        neighbour_job, _a, _b, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID_2, sku=self.HYPHENATED_NUMERIC_SKU,
        )
        neighbour = self.Decision.search([('job_id', '=', neighbour_job.id)])
        self.assertEqual(neighbour.state, 'pending')
        # A completely different product now raises, twice, at two versions.
        self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        self._drain(self._graphql_product(
            self.REAL_PRODUCT_GID,
            [self._graphql_variant(
                self.REAL_VARIANT_GID, sku=self.NUMERIC_SKU,
            )],
            updated_at=LATER_STAMP,
        ))
        neighbour.invalidate_recordset()
        self.assertEqual(
            neighbour.state, 'pending',
            'an unrelated product superseded this decision',
        )

    def test_one_confirmation_resumes_exactly_one_job(self):
        """§10.16, with two production-shaped decisions live at once."""
        job_a, first_a, _b, _s = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        job_b, _first_b, _b2, _s2 = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID_2, sku=self.HYPHENATED_NUMERIC_SKU,
        )
        decision_a = self.Decision.search([('job_id', '=', job_a.id)])
        self._confirm(decision_a, first_a)
        job_a.invalidate_recordset()
        job_b.invalidate_recordset()
        self.assertEqual(job_a.state, 'queued')
        self.assertEqual(job_b.state, 'blocked_manual_review')

    def test_generic_review_still_refuses_on_production_shaped_data(self):
        """§10.17. The §8.2.14 refusal is unchanged by the correction."""
        job, _first, _second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        with self.assertRaises(UserError) as ctx:
            job.with_user(
                self.roles['reviewer']
            ).action_resolve_manual_review()
        self.assertIn('match decision', str(ctx.exception))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')

    def test_identity_validation_refuses_shapes_it_cannot_carry(self):
        """`opaque_identity` validates and NEVER transforms."""
        for value in (
            self.REAL_PRODUCT_GID, self.REAL_VARIANT_GID, REMOTE_STAMP,
            ' leading and trailing ',
        ):
            self.assertEqual(
                opaque_identity(value, MATCH_GID_MAX_LEN), value,
                'identity validation altered %r' % (value,),
            )
        for refused in (
            '', None, False, 123, b'bytes', 'has\x00a null',
            'has\na newline', 'x' * (MATCH_GID_MAX_LEN + 1),
        ):
            self.assertEqual(opaque_identity(refused, MATCH_GID_MAX_LEN), '')

    def test_an_unusable_identity_records_no_decision_at_all(self):
        """Fail closed, not fail sanitized.

        A GID carrying a control character cannot be carried verbatim, and
        the correction refuses to invent a cleaned-up substitute for it. The
        job still blocks and simply offers no decision.
        """
        evidence = build_match_evidence(
            self.env,
            level=DECISION_LEVEL_TEMPLATE,
            shopify_product_gid='gid://shopify/Product/73462\x0099043911',
            remote_updated_at=REMOTE_STAMP,
            match_key='sku_reference',
            match_values=[self.NUMERIC_SKU],
            candidate_ids=[1, 2], candidate_total=2,
        )
        self.assertEqual(evidence, '')

    def test_a_digest_is_keyed_bounded_and_not_the_value(self):
        digest = match_value_digest(self.env, self.NUMERIC_SKU)
        self.assertEqual(len(digest), MATCH_DIGEST_LEN)
        self.assertNotIn(self.NUMERIC_SKU, digest)
        self.assertEqual(
            digest, match_value_digest(self.env, self.NUMERIC_SKU),
            'the digest must be stable within one database',
        )
        self.assertNotEqual(
            digest, match_value_digest(self.env, self.HYPHENATED_NUMERIC_SKU),
        )
        # Keyed on this database's own secret, so it is not a lookup table
        # entry for a 13-digit number.
        secret = self.env['ir.config_parameter'].sudo().get_param(
            'database.secret',
        )
        self.assertTrue(secret)
        self.assertNotEqual(
            digest,
            'v2:' + hashlib.sha256(
                self.NUMERIC_SKU.encode('utf-8')
            ).hexdigest(),
        )
        self.assertEqual(match_value_digest(self.env, ''), '')
        self.assertEqual(match_value_digest(self.env, None), '')

    # ==================================================================
    # K. THE BATCH 2 CORRECTION (F10): access is checked BEFORE the row
    #    lock, and the lock is still a real one.
    # ==================================================================

    def test_a_foreign_decision_is_refused_before_its_row_is_locked(self):
        """Proved by OBSERVING the database and the statements, not the source.

        `SELECT ... FOR UPDATE` by primary key is raw SQL and answers to no ACL
        and no record rule, so with the lock taken first a caller who names
        another company's decision id acquires a genuine write lock on that row
        -- blocking its legitimate reviewer for the life of the transaction --
        and only afterwards learns they were not allowed to be there.

        THE MEASUREMENT IS THE STATEMENTS ACTUALLY ISSUED, and it is not a
        source-string assertion: the cursor is wrapped for the duration of each
        call and every statement recorded, so this asserts what the code
        EXECUTED at runtime.

        Two alternatives were tried and rejected as instruments that cannot
        attribute a lock. `pg_locks` at relation level: `TransactionCase` shares
        one transaction across the whole class, so a lock taken by an earlier
        test is still held and PostgreSQL coalesces a second identical
        (relation, mode) entry into the first. The tuple's own `xmax`: the
        candidate m2m rows carry a foreign key to the decision, so inserting
        them takes `FOR KEY SHARE` on it and sets `xmax` before any caller has
        done anything at all.
        """
        job, first, _second, _sent = self._ambiguous_template_run(
            gid=self.REAL_PRODUCT_GID, sku=self.NUMERIC_SKU,
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertTrue(first)
        self.env.flush_all()

        def locking_statements(recorded):
            return [
                text for text in recorded
                if 'FOR UPDATE' in text.upper()
                and 'shopify_connector_product_match_decision' in text
            ]

        @contextmanager
        def recording():
            recorded = []
            cursor_type = type(self.env.cr)
            original = cursor_type.execute

            def spy(cr_self, query, params=None, log_exceptions=True):
                recorded.append(
                    query if isinstance(query, str)
                    else str(getattr(query, 'code', query))
                )
                return original(cr_self, query, params, log_exceptions)

            with patch.object(cursor_type, 'execute', spy):
                yield recorded

        wizard = self.Wizard.with_user(self.foreign_admin).with_context(
            default_decision_id=False,
        ).sudo().create({'decision_id': decision.id})

        with recording() as refused_statements:
            with self.assertRaises(Exception) as refusal:
                wizard.with_user(self.foreign_admin).action_confirm()
        self.assertIsInstance(refusal.exception, (AccessError, UserError))
        self.assertTrue(
            refused_statements,
            'no statement was recorded at all, so the instrument is not '
            'measuring the call it claims to measure',
        )
        self.assertFalse(
            locking_statements(refused_statements),
            'the refused caller issued a FOR UPDATE against the decision '
            'table before being refused',
        )

        # The lock itself is unchanged for a caller who IS allowed: the confirm
        # path still takes it, which is what the one-winner/one-refusal
        # concurrent-confirmation behaviour proved in section F rests on.
        with recording() as allowed_statements:
            self._confirm(decision, first)
        self.assertTrue(
            locking_statements(allowed_statements),
            'the authorized confirmation no longer takes a row lock, so the '
            'concurrent-confirmation refusal has lost its mechanism',
        )
