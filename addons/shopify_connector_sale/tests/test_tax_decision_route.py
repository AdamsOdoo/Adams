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

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_sale.models.shopify_connector_order_scan import (
    ORDER_SCAN_CRON_XMLID,
)
from odoo.addons.shopify_connector_sale.models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
    build_tax_fingerprint,
    eligible_sale_tax_domain,
    tax_posture_included,
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

    def _block_order_on_unknown_tax(self, target='gid://shopify/Order/9001'):
        """Produce a genuinely tax-blocked job through production code.

        The evidence is whatever `_resolve_taxes` actually raises, and the
        state is whatever the dispatcher's own `_route_failure` actually
        assigns for that error class. Hand-writing either would let this
        suite pass against a taxonomy the product no longer uses.

        `target` is a parameter because `operation_scope_key` is UNIQUE per
        store and target, so two blocked orders -- the shape a scan actually
        admits, and the shape the competing-choice tests need -- must name two
        different Shopify orders.
        """
        job = self._job(target=target)
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

    def test_needs_attention_opens_the_tax_mapping_decision(self):
        job, _detail = self._block_order_on_unknown_tax()
        action = job.with_user(
            self.roles['admin']
        ).action_open_attention_case()
        self.assertEqual(
            action['res_model'], 'shopify.connector.tax.decision.wizard',
        )
        self.assertEqual(action['target'], 'new')

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

    # ==================================================================
    # THE BATCH 2 CORRECTION (F4): eligibility reads Odoo's EFFECTIVE tax
    # inclusion posture, not an explicit override.
    #
    # `account.tax.price_include_override` is an OVERRIDE and is empty on an
    # ordinary tax. Odoo derives the real posture in `_compute_price_include`
    # (pin `30bde9ff`, `addons/account/models/account_tax.py`): the override
    # when set, otherwise `res.company.account_price_include`. Odoo's own
    # company default is `tax_excluded`, so requiring
    # `price_include_override == 'tax_excluded'` matched NO ordinary tax at
    # all -- every excluded Shopify tax on a default-configured company was
    # unmappable, and creating the tax the dialog asked for did not help
    # because the new tax also carried no override.
    #
    # Every fixture below whose posture is "inherited" leaves
    # `price_include_override` genuinely unset. It is never set merely to
    # make a test pass.
    # ==================================================================

    def _inherited_tax(self, name, amount=5.0, company=None):
        """A tax with NO `price_include_override` at all.

        The ordinary shape: a merchant creating a sale tax in the Odoo UI
        fills in a name and a rate and never touches "Included in Price".
        """
        company = company or self.env.company
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or self.env.ref('base.us')
        )
        group = self.env['account.tax.group'].sudo().create({
            'name': '%s Group' % name,
            'company_id': company.id,
            'country_id': country.id,
        })
        tax = self.env['account.tax'].sudo().create({
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'include_base_amount': False,
        })
        self.assertFalse(
            tax.price_include_override,
            'this fixture is worthless unless the override is genuinely '
            'unset',
        )
        return tax

    def _included_company_store(self):
        """A second company whose DEFAULT posture is tax-included.

        `account_price_include` cannot be changed once a company has started
        invoicing (`res.company._check_set_account_price_include`), so this
        builds a fresh company rather than flipping the shared one.
        """
        company = self.env['res.company'].sudo().create({
            'name': 'Tax posture included co',
            'account_price_include': 'tax_included',
        })
        self.assertEqual(company.account_price_include, 'tax_included')
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Tax posture included store',
            'shop_domain': 'tax-posture-included.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })
        pricelist = self.env['product.pricelist'].sudo().create({
            'name': 'Tax posture included pricelist',
            'currency_id': company.currency_id.id,
            'company_id': company.id,
        })
        partner = self.env['res.partner'].sudo().create({
            'name': 'Tax posture included fallback',
        })
        settings = self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'sale_domain_enabled': True,
            'order_company_id': company.id,
            'order_pricelist_id': pricelist.id,
            'order_payment_term_id': self.payment_term.id,
            'customer_fallback_partner_id': partner.id,
        })
        return company, store, settings

    def test_an_ordinary_tax_on_an_excluded_company_is_eligible(self):
        """§10 tax 1. The case that was completely unreachable.

        `self.env.company` uses Odoo's own default, `tax_excluded`, and the
        Shopify evidence here is an EXCLUDED tax. Before the correction this
        list came back empty for every such store in existence.
        """
        self.assertEqual(
            self.env.company.account_price_include, 'tax_excluded',
        )
        inherited = self._inherited_tax('Inherited excluded 5')
        self.assertFalse(inherited.price_include)
        job, _detail = self._block_order_on_unknown_tax()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            self.roles['admin']
        )
        offered = Wizard._eligible_tax_ids(job, job._tax_decision_evidence())
        self.assertIn(
            inherited.id, offered,
            'a tax whose posture is inherited from the company default was '
            'not offered',
        )

    def test_an_ordinary_tax_on_an_included_company_is_eligible(self):
        """§10 tax 2. The mirror case, on a company defaulting to included."""
        company, store, settings = self._included_company_store()
        inherited = self._inherited_tax(
            'Inherited included 5', company=company,
        )
        self.assertTrue(
            inherited.price_include,
            'the company default did not reach the tax',
        )
        job = self.Job.sudo().create({
            'store_id': store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': 'tax-posture-included',
            'shopify_target_gid': 'gid://shopify/Order/9101',
        })
        order = self.env['sale.order'].sudo().create({
            'partner_id': settings.customer_fallback_partner_id.id,
            'company_id': company.id,
            'pricelist_id': settings.order_pricelist_id.id,
            'payment_term_id': settings.order_payment_term_id.id,
        })
        with self.assertRaises(JobHandlerError) as blocked:
            self.Importer._resolve_taxes(
                order, store, [self._evidence()], True, settings,
            )
        exc = blocked.exception
        self.env['shopify.connector.job.dispatch']._route_failure(
            job, exc.error_class, exc.reason, exc.technical_detail,
        )
        job.invalidate_recordset()
        evidence = job._tax_decision_evidence()
        self.assertTrue(evidence)
        self.assertTrue(evidence['included'])
        Wizard = self.env['shopify.connector.tax.decision.wizard']
        self.assertIn(inherited.id, Wizard._eligible_tax_ids(job, evidence))

    def test_an_explicit_matching_override_is_still_eligible(self):
        """§10 tax 3. The correction widens; it does not replace."""
        explicit = self._tax(name='Explicit excluded 5', included=False)
        self.assertEqual(explicit.price_include_override, 'tax_excluded')
        job, _detail = self._block_order_on_unknown_tax()
        Wizard = self.env['shopify.connector.tax.decision.wizard']
        self.assertIn(
            explicit.id,
            Wizard._eligible_tax_ids(job, job._tax_decision_evidence()),
        )

    def test_a_mismatching_effective_posture_is_still_refused(self):
        """§10 tax 4. Both ways of getting it wrong, both refused."""
        explicit_wrong = self._tax(name='Explicit included 5', included=True)
        company, _store, _settings = self._included_company_store()
        inherited_wrong = self._inherited_tax(
            'Inherited included wrong 5', company=company,
        )
        self.assertTrue(explicit_wrong.price_include)
        self.assertTrue(inherited_wrong.price_include)
        job, _detail = self._block_order_on_unknown_tax()
        evidence = job._tax_decision_evidence()
        self.assertFalse(evidence['included'])
        Wizard = self.env['shopify.connector.tax.decision.wizard']
        offered = Wizard._eligible_tax_ids(job, evidence)
        self.assertNotIn(explicit_wrong.id, offered)
        self.assertNotIn(inherited_wrong.id, offered)
        # And the mapping constraint agrees, which is the point of the
        # shared rule.
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.tax.mapping'].sudo().create({
                'store_id': self.store.id,
                'shopify_tax_evidence_key': evidence['fingerprint'],
                'shopify_tax_fingerprint_version':
                    SHOPIFY_TAX_FINGERPRINT_VERSION,
                'shopify_price_included': False,
                'account_tax_id': explicit_wrong.id,
            })

    def test_the_wizard_and_the_constraint_share_one_effective_rule(self):
        """§4: one rule, or proved equivalent. This proves it.

        Every tax the database holds is put to both authorities -- the search
        predicate the dialog offers from, and the per-record predicate the
        mapping constraint enforces -- and they must agree on every one. A
        drift between them is exactly what F4 was.
        """
        self._tax(name='Equiv explicit excluded')
        self._tax(name='Equiv explicit included', included=True)
        self._tax(name='Equiv wrong rate', amount=7.0)
        self._tax(name='Equiv compound', include_base_amount=True)
        self._inherited_tax('Equiv inherited excluded')
        archived = self._tax(name='Equiv archived')
        archived.sudo().write({'active': False})
        self._foreign_tax('EquivForeign')
        company, _store, _settings = self._included_company_store()
        self._inherited_tax('Equiv inherited included', company=company)

        every_tax = self.env['account.tax'].sudo().with_context(
            active_test=False,
        ).search([])
        self.assertGreater(len(every_tax), 5)
        for price_included in (False, True):
            domain = eligible_sale_tax_domain(
                self.env.company, price_included, 5.0,
            )
            searched = set(self.env['account.tax'].sudo().search(domain).ids)
            per_record = {
                tax.id for tax in every_tax
                if tax.company_id == self.env.company
                and tax.active
                and tax.type_tax_use == 'sale'
                and tax.amount_type == 'percent'
                and abs(tax.amount - 5.0) < 1e-9
                and not tax.include_base_amount
                and tax_posture_included(tax) == price_included
            }
            self.assertEqual(
                searched, per_record,
                'the search predicate and the per-record predicate disagree '
                'for price_included=%s' % (price_included,),
            )

    def test_an_inherited_posture_tax_completes_the_whole_route(self):
        """§10 tax 5, on the shape a real merchant actually has.

        Blocked order -> dialog -> mapping -> the exact job resumes -> the
        importer's own validation accepts the mapping on the next attempt.
        That last step is what makes this end to end: `_validate_resolved_tax`
        is a third authority, and leaving it reading the raw override would
        have meant the merchant mapped the tax and the order still did not
        move.
        """
        inherited = self._inherited_tax('Route inherited 5')
        job, detail = self._block_order_on_unknown_tax()
        scans_before = self._scans()
        wizard = self._open_wizard(job, inherited)
        self.assertIn(inherited, wizard.candidate_tax_ids)
        wizard.action_confirm()
        mapping = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping.account_tax_id, inherited)
        self.assertEqual(
            mapping.shopify_tax_evidence_key, detail['fingerprint'],
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        self.assertEqual(self._scans(), scans_before)
        # The blocker really is gone for the resumed import.
        taxes, rate, _signatures = self.Importer._resolve_taxes(
            self._order(), self.store, [self._evidence()], False,
            self.settings,
        )
        self.assertEqual(taxes, inherited)
        self.assertEqual(str(rate), '5')

    # ==================================================================
    # THE BATCH 2 CORRECTION (F5): the dialog's identity is a validated
    # snapshot, and ordinary ORM create/write/read cannot reach past it.
    # ==================================================================

    def _foreign_blocked_job(self):
        """A genuinely tax-blocked job belonging to another company."""
        company = self.env['res.company'].sudo().create({
            'name': 'Tax wizard foreign co',
        })
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Tax wizard foreign store',
            'shop_domain': 'tax-wizard-foreign.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': company.id,
        })
        job = self.Job.sudo().create({
            'store_id': store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'failed_retryable',
            'error_class': 'odoo_validation_configuration',
            'payload_hash': 'tax-wizard-foreign',
            'shopify_target_gid': 'gid://shopify/Order/8800770066',
        })
        return company, store, job

    def test_no_related_field_walks_out_of_the_dialog_under_elevation(self):
        """The structural half of F5, and the reason snapshots exist.

        Odoo 19 gives a `related` field `compute_sudo=True` by default
        (`odoo/orm/fields.py`: `related_sudo` -> `compute_sudo`, and
        `Field.compute_value` calls `records.sudo()`), so a related chain
        through `job_id` answers as SUPERUSER whatever the caller's rights.
        These three fields carry the store, the company and the order GID, so
        a related chain here IS the disclosure.
        """
        Wizard = self.env['shopify.connector.tax.decision.wizard']
        for name in ('store_id', 'company_id', 'shopify_order_gid'):
            field = Wizard._fields[name]
            self.assertFalse(
                field.related,
                '%s is a related field again, so it is computed under '
                'elevation and discloses whatever job it is pointed at'
                % (name,),
            )

    def test_an_administrator_cannot_create_a_dialog_for_a_foreign_job(self):
        """§10 tax 6, on the ORDINARY create route rather than the UI one."""
        _company, _store, foreign_job = self._foreign_blocked_job()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            self.roles['admin']
        )
        with self.assertRaises(AccessError):
            Wizard.create({'job_id': foreign_job.id})
        with self.assertRaises(AccessError):
            Wizard.with_context(
                default_job_id=foreign_job.id
            ).create({})
        self.assertFalse(
            self.env['shopify.connector.tax.decision.wizard'].sudo().search([
                ('job_id', '=', foreign_job.id),
            ]),
            'a dialog row was created for a foreign job',
        )

    def test_an_administrator_cannot_move_a_dialog_onto_a_foreign_job(self):
        """§10 tax 6, the write route. Identity is immutable once open."""
        tax = self._inherited_tax('Immutable identity 5')
        job, _detail = self._block_order_on_unknown_tax()
        _company, foreign_store, foreign_job = self._foreign_blocked_job()
        wizard = self._open_wizard(job, tax)
        for vals in (
            {'job_id': foreign_job.id},
            {'store_id': foreign_store.id},
            {'shopify_order_gid': 'gid://shopify/Order/8800770066'},
            {'shopify_tax_evidence_key': 'v1:' + 'a' * 64},
        ):
            with self.assertRaises(UserError, msg=str(vals)):
                wizard.with_user(self.roles['admin']).write(vals)
        wizard.invalidate_recordset()
        self.assertEqual(wizard.job_id, job)
        self.assertEqual(wizard.store_id, self.store)
        # The one thing the administrator IS deciding stays writable.
        other = self._inherited_tax('Immutable identity other 5')
        wizard.with_user(self.roles['admin']).write({
            'account_tax_id': other.id,
        })
        self.assertEqual(wizard.account_tax_id, other)

    def test_the_refusal_discloses_nothing_about_the_foreign_job(self):
        """§10 tax 7. The message is the disclosure surface, so it is checked.

        Odoo's own access errors name the records they refuse; for a
        cross-company probe that is the leak the check exists to prevent.
        """
        company, store, foreign_job = self._foreign_blocked_job()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            self.roles['admin']
        )
        with self.assertRaises(AccessError) as refused:
            Wizard.create({'job_id': foreign_job.id})
        message = str(refused.exception)
        for secret in (
            store.name, store.shop_domain, company.name,
            foreign_job.shopify_target_gid, str(store.id), str(company.id),
        ):
            self.assertNotIn(
                secret, message,
                'the refusal disclosed %r about a foreign company' % (secret,),
            )

    def test_one_administrator_cannot_read_another_open_dialog(self):
        """§10 tax 6, the READ route, and F5 invariant 9.

        Odoo 19's `TransientModel` no longer restricts a transient row to its
        creator (`odoo/orm/models_transient.py` at the pin has no
        `_check_access` override, despite its docstring), and the ACL grants
        every Connector Administrator full CRUD -- so the ownership rule this
        correction adds is the only thing standing between one administrator
        and another's open dialog, snapshot and all.
        """
        tax = self._inherited_tax('Dialog ownership 5')
        job, _detail = self._block_order_on_unknown_tax()
        wizard = self._open_wizard(job, tax)
        other_admin = self.env['res.users'].sudo().create({
            'name': 'Tax decision second admin',
            'login': 'tax_decision_second_admin',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })
        self.assertFalse(
            wizard.with_user(other_admin).has_access('read'),
            'another administrator can read this open dialog',
        )
        with self.assertRaises(AccessError):
            wizard.with_user(other_admin).read(['store_id', 'job_id'])
        # Its own opener is unaffected.
        self.assertTrue(
            wizard.with_user(self.roles['admin']).has_access('read'),
        )

    # ==================================================================
    # THE BATCH 2 CORRECTION (F6): a uniqueness collision never substitutes
    # a different administrator's tax choice for this one.
    # ==================================================================

    def test_an_identical_earlier_mapping_is_proved_before_it_is_reused(self):
        """The one branch that may return a row it did not create.

        TWO orders are blocked on the SAME fingerprint before anything is
        mapped -- the ordinary shape, since a scan admits a window of orders
        at once. Deciding the first creates the mapping; deciding the second
        meets the unique index with the winning row already in this
        transaction's snapshot. Refusing there would be a usability regression
        with no safety gain, so it proceeds -- but only after PROVING the
        existing row is the same store, fingerprint, version, posture and
        Odoo tax.
        """
        tax = self._inherited_tax('Sequential 5')
        first_job, detail = self._block_order_on_unknown_tax()
        second_job, second_detail = self._block_order_on_unknown_tax(
            target='gid://shopify/Order/9003',
        )
        self.assertNotEqual(first_job, second_job)
        self.assertEqual(detail['fingerprint'], second_detail['fingerprint'])

        self._open_wizard(first_job, tax).action_confirm()
        first_job.invalidate_recordset()
        self.assertEqual(first_job.state, 'queued')

        second_wizard = self._open_wizard(second_job, tax)
        second_wizard.action_confirm()
        second_job.invalidate_recordset()
        self.assertEqual(
            second_job.state, 'queued',
            'the second order was blocked on the same fingerprint and the '
            'same choice, so it must resume rather than be refused',
        )
        mappings = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings.account_tax_id, tax)

    def test_a_different_choice_against_an_existing_mapping_refuses(self):
        """§10 tax 8/9 for the visible-row case.

        Same two-blocked-orders shape, but the second administrator picks a
        DIFFERENT tax. Returning the existing row here would report their
        decision as applied and resume the order under a mapping they never
        chose -- which is precisely what the previous implementation did.
        """
        mine = self._inherited_tax('Visible race mine 5')
        theirs = self._inherited_tax('Visible race theirs 5')
        first_job, _detail = self._block_order_on_unknown_tax()
        second_job, _detail2 = self._block_order_on_unknown_tax(
            target='gid://shopify/Order/9004',
        )
        self._open_wizard(first_job, mine).action_confirm()

        second_wizard = self._open_wizard(second_job, theirs)
        with self.assertRaises(UserError) as refused:
            second_wizard.action_confirm()
        self.assertIn('not applied', str(refused.exception))
        second_job.invalidate_recordset()
        self.assertEqual(
            second_job.state, 'failed_retryable',
            'a refused decision must not resume the order',
        )
        mappings = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mappings), 1)
        self.assertEqual(
            mappings.account_tax_id, mine,
            'the refused choice replaced the mapping that had already won',
        )

    # ==================================================================
    # THE BATCH 2 CORRECTION (F7): "scheduled" means the cron is really on.
    # ==================================================================

    def test_scheduled_state_is_false_while_the_real_cron_is_disabled(self):
        """§10 schedule 1/2. The flag is an intention; the cron is the fact."""
        cron = self.env.ref(ORDER_SCAN_CRON_XMLID)
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        self.store.invalidate_recordset()
        self.assertTrue(cron.active)
        self.assertTrue(self.store.order_sync_scheduled)

        cron.sudo().write({'active': False})
        self.store.invalidate_recordset()
        self.env.registry.clear_cache()
        self.assertFalse(
            self.store.order_sync_scheduled,
            'the store still claims scheduled import while the cron that '
            'would perform it is disabled',
        )
        cron.sudo().write({'active': True})
        self.store.invalidate_recordset()
        self.assertTrue(self.store.order_sync_scheduled)

    def test_the_domain_flag_still_governs_the_scheduled_claim(self):
        """§10 schedule 3."""
        self.settings.write({
            'sale_domain_enabled': False,
            'order_scheduled_sync_enabled': True,
        })
        self.store.invalidate_recordset()
        self.assertFalse(self.store.order_sync_scheduled)

    def test_manual_import_survives_a_disabled_cron_and_stays_role_gated(self):
        """§10 schedule 4. Truthfulness must not remove the manual route."""
        self.env.ref(ORDER_SCAN_CRON_XMLID).sudo().write({'active': False})
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        self.store.invalidate_recordset()
        self.assertFalse(self.store.order_sync_scheduled)
        scan = self.store.with_user(
            self.roles['operator']
        ).action_sync_orders_now()
        self.assertTrue(scan)
        self.assertEqual(scan.job_type, 'order_import_scan')
        with self.assertRaises(AccessError):
            self.store.with_user(self.roles['auditor']).action_sync_orders_now()
