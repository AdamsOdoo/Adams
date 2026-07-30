"""Batch 2 checkpoint 2 -- order controls, and the tax blocked-work route.

Every test here drives a production path: an ordinary model write that the
canonical settings form performs, the real cron entry point, the real store
and binding actions, the dispatcher's own failure routing, and the wizard's
public methods. Nothing constructs a job state by hand that production would
not produce the same way.
"""

import json
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_sale.models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
    build_tax_fingerprint,
)
from odoo.addons.shopify_connector_sale.wizards.shopify_connector_tax_decision_wizard import (
    parse_tax_evidence,
)

from .test_order_import_mapping import OrderImportCase

VIEWS_ROOT = Path(__file__).resolve().parent.parent / 'views'


@tagged('post_install', '-at_install')
class TestTaxDecisionRoute(OrderImportCase):

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------

    def _tax(self, name='VAT 5', amount=5.0, included=False, **extra):
        company = self.env.company
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or self.env.ref('base.us')
        )
        tax_group = self.env['account.tax.group'].sudo().create({
            'name': '%s Group' % name,
            'company_id': company.id,
            'country_id': country.id,
        })
        values = {
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': tax_group.id,
            'price_include_override': (
                'tax_included' if included else 'tax_excluded'
            ),
            'include_base_amount': False,
        }
        values.update(extra)
        return self.env['account.tax'].sudo().create(values)

    def _evidence(self, title='VAT', source='Shopify', liable=None):
        return {
            'title': title,
            'source': source,
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': liable,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }

    def _order(self):
        return self.env['sale.order'].create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
        })

    def _foreign_tax(self, label):
        """A same-rate, same-posture sale tax in a DIFFERENT company.

        The whole point is that it is indistinguishable from an eligible one
        on every axis except ownership, so a candidate query that forgot the
        company filter would happily offer it.
        """
        company = self.env['res.company'].sudo().create({'name': label})
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or self.env.ref('base.us')
        )
        group = self.env['account.tax.group'].sudo().create({
            'name': '%s Group' % label,
            'company_id': company.id,
            'country_id': country.id,
        })
        return self.env['account.tax'].sudo().create({
            'name': '%s 5' % label,
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'price_include_override': 'tax_excluded',
            'include_base_amount': False,
        })

    def _binding(self, gid):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'sale_order_id': self._order().id,
        })

    def _block_order_on_unknown_tax(self):
        """Produce a genuinely tax-blocked job through production code.

        The evidence is whatever `_resolve_taxes` actually raises, and the
        state is whatever the dispatcher's own `_route_failure` actually
        assigns for that error class. Hand-writing either would let this
        suite pass against a taxonomy the product no longer uses.
        """
        job = self._job(target='gid://shopify/Order/9001')
        with self.assertRaises(JobHandlerError) as blocked:
            self.Importer._resolve_taxes(
                self._order(), self.store, [self._evidence()], False,
                self.settings,
            )
        exc = blocked.exception
        self.env['shopify.connector.job.dispatch']._route_failure(
            job, exc.error_class, exc.reason, exc.technical_detail,
        )
        job.invalidate_recordset()
        return job, json.loads(exc.technical_detail)

    def _scans(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])

    # ------------------------------------------------------------------
    # §7.1 -- the order controls, and the scheduled path
    # ------------------------------------------------------------------

    def test_settings_write_makes_the_real_cron_admit_one_scan(self):
        """The proof §7.1 asks for, end to end at the model layer.

        The write is exactly what the canonical Store Settings form performs
        -- an ordinary `write` on the settings record as an Administrator --
        and the admission is the real cron entry point, not a helper.
        """
        self.settings.with_user(self.roles['admin']).write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        self.assertFalse(self._scans())
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        scans = self._scans()
        self.assertEqual(len(scans), 1)
        self.assertEqual(scans.job_source, 'scheduled_sync')
        self.assertEqual(scans.shopify_target_gid, 'scan:order')

    def test_disabled_scheduling_admits_nothing_and_the_store_says_so(self):
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': False,
        })
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        self.assertFalse(self._scans())
        self.store.invalidate_recordset()
        self.assertFalse(
            self.store.order_sync_scheduled,
            'The store form must be able to say scheduling is off; a manual '
            'button beside a silent screen reads as "this is handled".',
        )
        self.assertTrue(self.store.order_sync_domain_enabled)

    def test_manual_and_scheduled_admission_coalesce(self):
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        manual = self.store.with_user(
            self.roles['operator']
        ).action_sync_orders_now()
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        again = self.store.with_user(
            self.roles['admin']
        ).action_sync_orders_now()
        self.assertEqual(len(self._scans()), 1)
        self.assertEqual(again, manual)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.order_sync_active_scan_count, 1)

    def test_binding_refresh_admits_one_per_gid_import_job(self):
        binding = self._binding('gid://shopify/Order/7700')
        first = binding.with_user(self.roles['operator']).action_sync_selected()
        second = binding.with_user(self.roles['admin']).action_sync_selected()
        self.assertEqual(first, second)
        self.assertEqual(first.job_type, 'order_import_sync')
        self.assertEqual(first.shopify_target_gid, 'gid://shopify/Order/7700')
        self.assertEqual(len(self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', 'gid://shopify/Order/7700'),
        ])), 1)

    def test_binding_refresh_is_role_gated(self):
        binding = self._binding('gid://shopify/Order/7701')
        for role in ('auditor', 'reviewer'):
            with self.assertRaises(AccessError, msg=role):
                binding.with_user(self.roles[role]).action_sync_selected()

    def test_production_views_bind_the_existing_methods_not_the_importer(self):
        """§7.1.7: no direct UI call to the single-order importer.

        A view that called `import_order_sync` would run a Shopify read on the
        web worker, outside the job substrate that owns retry, classification
        and audit for every other import.
        """
        controls = (
            VIEWS_ROOT / 'shopify_connector_order_controls_views.xml'
        ).read_text(encoding='utf-8')
        self.assertIn('action_sync_orders_now', controls)
        self.assertIn('action_sync_selected', controls)
        for view_file in VIEWS_ROOT.glob('*.xml'):
            text = view_file.read_text(encoding='utf-8')
            for forbidden in ('import_order_sync', '_resolve_taxes'):
                self.assertNotIn(
                    forbidden, text,
                    '%s calls %s directly from a view.' % (
                        view_file.name, forbidden,
                    ),
                )

    # ------------------------------------------------------------------
    # §7.2 -- the tax decision route
    # ------------------------------------------------------------------

    def test_unknown_fingerprint_becomes_actionable_work(self):
        job, detail = self._block_order_on_unknown_tax()
        self.assertEqual(job.state, 'failed_retryable')
        self.assertEqual(job.error_class, 'odoo_validation_configuration')
        self.assertTrue(
            job.tax_decision_pending,
            'A tax-blocked order must offer its decision route.',
        )
        evidence = job._tax_decision_evidence()
        self.assertEqual(evidence['fingerprint'], detail['fingerprint'])
        self.assertEqual(
            evidence['suggestion_basis'],
            'rate_and_inclusion_only_non_binding',
        )

    def test_a_healthy_job_offers_no_decision_route(self):
        job = self._job()
        self.assertFalse(job.tax_decision_pending)

    def test_malformed_or_substituted_evidence_is_refused(self):
        job, detail = self._block_order_on_unknown_tax()
        log = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)], order='id desc', limit=1,
        )
        substitutions = (
            'not json at all',
            json.dumps({'fingerprint': detail['fingerprint']}),
            json.dumps(dict(detail, extra_key='smuggled')),
            json.dumps(dict(detail, fingerprint='v1:' + 'z' * 64)),
            json.dumps(dict(detail, fingerprint='v9:' + 'a' * 64)),
            json.dumps(dict(detail, suggested_account_tax_ids='all of them')),
            json.dumps(dict(detail, included='yes')),
        )
        for payload in substitutions:
            log.sudo().write({'technical_detail': payload})
            job.invalidate_recordset()
            self.assertFalse(
                parse_tax_evidence(payload),
                'accepted a substituted payload: %s' % payload[:60],
            )
            self.assertFalse(job.tax_decision_pending)
            with self.assertRaises(UserError):
                job.with_user(
                    self.roles['admin']
                ).action_open_tax_mapping_decision()

    def test_the_reason_sentence_is_never_the_identity_source(self):
        """§7.2.4: rewording the human message must change nothing."""
        job, detail = self._block_order_on_unknown_tax()
        log = self.env['shopify.connector.job.log'].search(
            [('job_id', '=', job.id)], order='id desc', limit=1,
        )
        log.sudo().write({'message': 'Completely different wording.'})
        job.invalidate_recordset()
        self.assertTrue(job.tax_decision_pending)
        self.assertEqual(
            job._tax_decision_evidence()['fingerprint'], detail['fingerprint'],
        )

    def test_candidates_are_bounded_same_company_and_right_posture(self):
        eligible = self._tax(name='Eligible 5')
        wrong_rate = self._tax(name='Wrong rate', amount=7.0)
        wrong_posture = self._tax(name='Wrong posture', included=True)
        archived = self._tax(name='Archived 5')
        archived.sudo().write({'active': False})
        foreign = self._foreign_tax('TaxDecisionForeign')
        job, detail = self._block_order_on_unknown_tax()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            self.roles['admin']
        )
        offered = Wizard._eligible_tax_ids(job, job._tax_decision_evidence())
        self.assertIn(eligible.id, offered)
        for excluded in (wrong_rate, wrong_posture, archived, foreign):
            self.assertNotIn(excluded.id, offered, excluded.name)

    def test_a_multi_company_admin_is_still_not_offered_a_foreign_tax(self):
        """The company filter's real job, isolated from the record rule.

        For an ordinary single-company administrator, Odoo's own multi-company
        rule on `account.tax` already hides another company's taxes, so the
        candidate query's explicit `company_id` filter is invisible: removing
        it changes nothing and no test notices. This user has BOTH companies
        active, so the record rule lets the foreign tax through and the only
        thing standing between it and the dropdown is the filter itself.
        """
        foreign = self._foreign_tax('TaxDecisionMultiCo')
        eligible = self._tax(name='Eligible multi 5')
        multi_admin = self.env['res.users'].sudo().create({
            'name': 'Tax decision multi-company admin',
            'login': 'tax_decision_multi_admin',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [
                self.env.company.id, foreign.company_id.id,
            ])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
                self.env.ref('base.group_multi_company').id,
            ])],
        })
        job, _detail = self._block_order_on_unknown_tax()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            multi_admin
        ).with_context(allowed_company_ids=[
            self.env.company.id, foreign.company_id.id,
        ])
        # The record rule really does let this user see it, so the exclusion
        # below cannot be the rule doing the work.
        self.assertIn(
            foreign,
            self.env['account.tax'].with_user(multi_admin).with_context(
                allowed_company_ids=[
                    self.env.company.id, foreign.company_id.id,
                ]
            ).search([('id', '=', foreign.id)]),
        )
        offered = Wizard._eligible_tax_ids(job, job._tax_decision_evidence())
        self.assertIn(eligible.id, offered)
        self.assertNotIn(
            foreign.id, offered,
            'a tax owned by another company was offered as a candidate',
        )

    def test_only_an_administrator_may_open_or_confirm(self):
        job, _detail = self._block_order_on_unknown_tax()
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError, msg=role):
                job.with_user(
                    self.roles[role]
                ).action_open_tax_mapping_decision()

    def test_confirmation_persists_evidence_and_resumes_the_exact_job(self):
        tax = self._tax()
        job, detail = self._block_order_on_unknown_tax()
        other_scans_before = self._scans()
        wizard = self._open_wizard(job, tax)
        self.assertEqual(
            wizard.shopify_tax_evidence_key, detail['fingerprint'],
        )
        self.assertIn(tax, wizard.candidate_tax_ids)
        result = wizard.action_confirm()

        mapping = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping.shopify_tax_evidence_key, detail['fingerprint'])
        self.assertEqual(mapping.account_tax_id, tax)
        self.assertEqual(
            mapping.shopify_tax_fingerprint_version,
            SHOPIFY_TAX_FINGERPRINT_VERSION,
        )
        self.assertEqual(mapping.company_id, self.store.company_id)
        self.assertEqual(result['res_id'], mapping.id)

        job.invalidate_recordset()
        self.assertEqual(
            job.state, 'queued',
            'The exact blocked job must resume, not a new one.',
        )
        self.assertEqual(
            self._scans(), other_scans_before,
            'Resuming must not create a fresh order scan.',
        )

    def test_a_second_confirmation_adds_no_mapping_and_no_second_resume(self):
        tax = self._tax()
        job, _detail = self._block_order_on_unknown_tax()
        first = self._open_wizard(job, tax)
        second = self._open_wizard(job, tax)
        first.action_confirm()
        job.invalidate_recordset()
        resumed_state = job.state
        # The second dialog was opened against the same evidence and is
        # confirmed after the first has already won.
        with self.assertRaises(UserError):
            second.action_confirm()
        self.assertEqual(
            self.env['shopify.connector.tax.mapping'].search_count([
                ('store_id', '=', self.store.id),
            ]), 1,
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, resumed_state)

    def test_confirmation_refuses_a_tax_that_stopped_being_eligible(self):
        tax = self._tax()
        job, _detail = self._block_order_on_unknown_tax()
        wizard = self._open_wizard(job, tax)
        tax.sudo().write({'active': False})
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.assertFalse(self.env['shopify.connector.tax.mapping'].search([]))

    def test_confirmation_refuses_a_foreign_company_tax(self):
        foreign = self._foreign_tax('TaxDecisionOther')
        job, _detail = self._block_order_on_unknown_tax()
        wizard = self._open_wizard(job, foreign)
        with self.assertRaises(UserError):
            wizard.action_confirm()
        self.assertFalse(self.env['shopify.connector.tax.mapping'].search([]))

    def test_generic_review_resolution_refuses_a_tax_blocked_job(self):
        """§7.2.13, and it is already true rather than newly built.

        `action_resolve_manual_review` admits only `blocked_manual_review`, and an
        unknown fingerprint routes to `failed_retryable`. Asserted here so the
        day the taxonomy moves, this says so instead of quietly allowing a
        requeue with no decision behind it.
        """
        job, _detail = self._block_order_on_unknown_tax()
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_resolve_manual_review()
        self.assertFalse(
            self.env['shopify.connector.tax.mapping'].search([]),
        )

    def test_retry_after_mapping_passes_the_prior_tax_blocker(self):
        tax = self._tax()
        job, _detail = self._block_order_on_unknown_tax()
        wizard = self._open_wizard(job, tax)
        wizard.action_confirm()
        taxes, rate, signatures = self.Importer._resolve_taxes(
            self._order(), self.store, [self._evidence()], False,
            self.settings,
        )
        self.assertEqual(taxes, tax)
        self.assertEqual(str(rate), '5')
        self.assertEqual(
            signatures,
            (build_tax_fingerprint(0.05, 5.0, 'VAT', 'Shopify', None, False),),
        )

    def test_the_whole_flow_makes_no_shopify_request(self):
        tax = self._tax()
        client = self.env['shopify.connector.api.client']

        def refuse(*args, **kwargs):
            raise AssertionError('the tax decision flow contacted Shopify')

        with patch.object(type(client), 'execute_business', new=refuse):
            job, _detail = self._block_order_on_unknown_tax()
            wizard = self._open_wizard(job, tax)
            wizard.action_confirm()
        self.assertEqual(
            self.env['shopify.connector.tax.mapping'].search_count([]), 1,
        )

    def test_no_shopify_mutation_exists_in_the_decision_source(self):
        """Structural, and about CALLS rather than about the word.

        An earlier version asserted the string 'mutation' was absent, which
        this file's own prose defeats -- and which would have passed for any
        implementation that simply avoided the word while still calling one.
        These are the actual transport entry points.
        """
        import ast
        path = (
            Path(__file__).resolve().parent.parent
            / 'wizards' / 'shopify_connector_tax_decision_wizard.py'
        )
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        forbidden = {
            'execute_mutation', '_send', '_send_lifecycle',
            '_send_token_exchange', 'execute_business', 'import_order_sync',
        }
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            called & forbidden,
            'the tax decision route calls a Shopify transport entry point: '
            '%s' % sorted(called & forbidden),
        )

    # ------------------------------------------------------------------
    # helper
    # ------------------------------------------------------------------

    def _open_wizard(self, job, tax=None):
        """Open the dialog the way the web client does.

        `default_get` fills the evidence, the user picks a tax, and the record
        is created with both when the button is pressed -- a wizard record is
        never created empty and then written. `account_tax_id` is `required`,
        so creating without it would fail at the database rather than at the
        guard under test.
        """
        admin = self.roles['admin']
        action = job.with_user(admin).action_open_tax_mapping_decision()
        self.assertEqual(
            action['res_model'], 'shopify.connector.tax.decision.wizard',
        )
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            admin
        ).with_context(**action['context'])
        values = dict(Wizard.default_get(list(Wizard._fields)))
        if tax is not None:
            values['account_tax_id'] = tax.id
        return Wizard.create(values)
