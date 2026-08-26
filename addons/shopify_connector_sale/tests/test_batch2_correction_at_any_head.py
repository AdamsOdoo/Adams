"""Batch 2 correction (F4, F5, F6, F7) — reproducers that run at ANY head.

Separate from `test_tax_decision_route.py` for the same reason its product
twin is separate: that file imports symbols the correction introduced
(`eligible_sale_tax_domain`, `tax_posture_included`, `ORDER_SCAN_CRON_XMLID`),
so at the pre-correction head it would fail at IMPORT time and prove nothing.
Everything here drives public production routes and imports nothing the
starting head `ccad8bf432868650abb80bfb2103bd8d397be549` does not already have.

Zero Shopify contact: the blocked job is produced by the real `_resolve_taxes`
refusal, which reaches no transport at all.
"""

import json

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_sale.models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
)

from .test_order_import_mapping import OrderImportCase
from odoo.tools import mute_logger

ORDER_SCAN_CRON_XMLID = (
    'shopify_connector_sale.ir_cron_shopify_connector_order_scan'
)


@tagged('post_install', '-at_install')
class TestBatch2SaleCorrectionAtAnyHead(OrderImportCase):

    # -- fixtures ------------------------------------------------------

    def _evidence(self, title='VAT'):
        return {
            'title': title,
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
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

    def _inherited_tax(self, name, company=None):
        """An ordinary sale tax with NO `price_include_override` at all.

        The shape a merchant creating a tax in the Odoo UI actually produces:
        they fill in a name and a rate and never touch "Included in Price".
        Odoo then derives the real posture from the company default
        (`res.company.account_price_include`, itself defaulting to
        `tax_excluded`), which is what `account.tax.price_include` computes.
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
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'include_base_amount': False,
        })
        self.assertFalse(
            tax.price_include_override,
            'this fixture is worthless unless the override is genuinely unset',
        )
        return tax

    def _explicit_tax(self, name):
        """A sale tax with the EXPLICIT override the old rule demanded.

        Used by the F6 reproducer so that it isolates the concurrent-choice
        defect: an inherited-posture tax is not eligible at the pre-correction
        head at all (that is F4), so a race test built on one would stop at the
        wrong refusal and say nothing about F6.
        """
        company = self.env.company
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
        return self.env['account.tax'].sudo().create({
            'name': name,
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'price_include_override': 'tax_excluded',
            'include_base_amount': False,
        })

    def _blocked(self, target='gid://shopify/Order/9001'):
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

    def _open_wizard(self, job, tax):
        admin = self.roles['admin']
        action = job.with_user(admin).action_open_tax_mapping_decision()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            admin
        ).with_context(**action['context'])
        values = dict(Wizard.default_get(list(Wizard._fields)))
        values['account_tax_id'] = tax.id
        return Wizard.create(values)

    def _foreign_blocked_job(self):
        company = self.env['res.company'].sudo().create({
            'name': 'Any-head foreign co',
        })
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Any-head foreign store',
            'shop_domain': 'any-head-foreign.myshopify.com',
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
            'payload_hash': 'any-head-foreign',
            'shopify_target_gid': 'gid://shopify/Order/8800770066',
        })
        return company, store, job

    # -- F4 ------------------------------------------------------------

    def test_an_ordinary_tax_is_eligible_for_an_excluded_shopify_tax(self):
        """The case that was completely unreachable at the starting head.

        `self.env.company` uses Odoo's own default posture, `tax_excluded`,
        and the Shopify evidence here is an EXCLUDED tax -- so an ordinary
        sale tax at the right rate IS the right answer. Requiring an explicit
        `price_include_override` meant no such tax was ever offered, the
        dialog told the merchant to create the tax and come back, and creating
        it did not help because the new tax also carried no override.
        """
        self.assertEqual(
            self.env.company.account_price_include, 'tax_excluded',
        )
        inherited = self._inherited_tax('Any-head inherited 5')
        self.assertFalse(inherited.price_include)
        job, _detail = self._blocked()
        Wizard = self.env['shopify.connector.tax.decision.wizard']
        offered = Wizard._eligible_tax_ids(job, job._tax_decision_evidence())
        self.assertIn(
            inherited.id, offered,
            'a tax whose inclusion posture is inherited from the company '
            'default was not offered, so a merchant on a default-configured '
            'company can map nothing at all',
        )

    def test_the_whole_tax_route_completes_on_an_ordinary_tax(self):
        """Blocked order -> dialog -> mapping -> the exact job resumes -> the
        importer's own validation accepts the mapping on the next attempt.

        That last step matters: `_validate_resolved_tax` is a third authority,
        so a mapping created through the dialog could still be refused on the
        very next import -- the merchant maps the tax and the order does not
        move.
        """
        inherited = self._inherited_tax('Any-head route 5')
        job, detail = self._blocked()
        wizard = self._open_wizard(job, inherited)
        self.assertIn(
            inherited, wizard.candidate_tax_ids,
            'the ordinary tax was not even offered as a candidate',
        )
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
        taxes, rate, _signatures = self.Importer._resolve_taxes(
            self._order(), self.store, [self._evidence()], False,
            self.settings,
        )
        self.assertEqual(
            taxes, inherited,
            'the mapping the merchant just made was refused by the importer '
            'on the next attempt',
        )
        self.assertEqual(str(rate), '5')

    # -- F5 ------------------------------------------------------------

    def test_an_administrator_cannot_reach_a_foreign_job_through_the_dialog(self):
        """`store_id`, `company_id` and `shopify_order_gid` were `related`
        fields through `job_id`, and Odoo 19 computes a related field under
        `sudo()` by default -- so an ordinary `create` naming a foreign job
        read back that store, that company and that order GID, none of which
        any record rule would have shown this administrator."""
        company, store, foreign_job = self._foreign_blocked_job()
        # `account_tax_id` is `required`, so a create without one fails at the
        # database rather than at the guard under test. Supplying a perfectly
        # ordinary local tax makes the create otherwise valid, which is what
        # makes this about the JOB the dialog is pointed at.
        local_tax = self._explicit_tax('Any-head disclosure probe 5')
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            self.roles['admin']
        )
        # `assertRaises` on this Odoo version does not accept a tuple, and a
        # bare `assertRaises(Exception)` would also swallow the `self.fail`
        # below -- so the disclosure is named explicitly instead.
        try:
            wizard = Wizard.create({
                'job_id': foreign_job.id,
                'account_tax_id': local_tax.id,
            })
        except (AccessError, UserError) as refused:
            message = str(refused)
        else:
            self.fail(
                'a company-A administrator created a tax decision dialog for '
                'a company-B job and can read store %r, company %r and order '
                '%r from it' % (
                    wizard.store_id.name, wizard.company_id.name,
                    wizard.shopify_order_gid,
                )
            )
        for secret in (
            store.name, store.shop_domain, company.name,
            foreign_job.shopify_target_gid,
        ):
            self.assertNotIn(
                secret, message,
                'the refusal disclosed %r about a foreign company' % (secret,),
            )
        self.assertFalse(
            self.env['shopify.connector.tax.decision.wizard'].sudo().search([
                ('job_id', '=', foreign_job.id),
            ]),
            'a dialog row was created for a foreign job',
        )

    def test_one_administrator_cannot_read_another_open_dialog(self):
        """Odoo 19's `TransientModel` no longer restricts a transient row to
        its creator, and the ACL grants every Connector Administrator full
        CRUD -- so without an ownership rule one administrator reads another's
        open dialog, snapshot and all."""
        tax = self._inherited_tax('Any-head ownership 5')
        job, _detail = self._blocked()
        wizard = self._open_wizard(job, tax)
        other_admin = self.env['res.users'].sudo().create({
            'name': 'Any-head second admin',
            'login': 'any_head_second_admin',
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

    # -- F6 ------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_a_different_choice_never_replaces_the_mapping_that_won(self):
        """Two orders blocked on one fingerprint; two administrators choose
        differently. At the starting head the loser's `IntegrityError` was
        caught, the winning row returned as the call's own result, and the
        order resumed under a tax the loser had never chosen and was never
        shown -- reported as success."""
        mine = self._explicit_tax('Any-head race mine 5')
        theirs = self._explicit_tax('Any-head race theirs 5')
        first_job, _detail = self._blocked()
        second_job, _detail2 = self._blocked(
            target='gid://shopify/Order/9005',
        )
        self._open_wizard(first_job, mine).action_confirm()

        second_wizard = self._open_wizard(second_job, theirs)
        with self.assertRaises(UserError):
            second_wizard.action_confirm()
        second_job.invalidate_recordset()
        self.assertEqual(
            second_job.state, 'failed_retryable',
            'a decision that was NOT applied resumed the order anyway',
        )
        mappings = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mappings), 1)
        self.assertEqual(
            mappings.account_tax_id, mine,
            'the refused choice replaced or duplicated the mapping that had '
            'already won',
        )
        self.assertEqual(
            mappings.shopify_tax_fingerprint_version,
            SHOPIFY_TAX_FINGERPRINT_VERSION,
        )

    # -- F7 ------------------------------------------------------------

    def test_scheduled_order_state_is_false_while_the_cron_is_disabled(self):
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
        self.assertFalse(
            self.store.order_sync_scheduled,
            'the store claims scheduled order import while the cron that '
            'would perform it is disabled',
        )
        self.assertTrue(self.store.order_sync_domain_enabled)

        cron.sudo().write({'active': True})
        self.store.invalidate_recordset()
        self.assertTrue(self.store.order_sync_scheduled)

    def test_manual_order_import_survives_a_disabled_cron(self):
        self.env.ref(ORDER_SCAN_CRON_XMLID).sudo().write({'active': False})
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        self.store.invalidate_recordset()
        scan = self.store.with_user(
            self.roles['operator']
        ).action_sync_orders_now()
        self.assertEqual(scan.job_type, 'order_import_scan')
        with self.assertRaises(AccessError):
            self.store.with_user(
                self.roles['auditor']
            ).action_sync_orders_now()
