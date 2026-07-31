"""Batch 2 correction (F6): the tax mapping race, across a REAL boundary.

WHY THIS FILE IS `-standard` AND USES GENUINE CONNECTIONS
--------------------------------------------------------

The defect is a uniqueness race, and a uniqueness race cannot happen on one
PostgreSQL session. `TransactionCase` runs everything on a single cursor, so a
"concurrent" administrator simulated there is the same transaction as the one
it is meant to overtake -- it sees its own uncommitted writes, and the unique
index it is supposed to lose to is one it has already satisfied.

Patching `Mapping.create` to raise `IntegrityError` on demand would exercise
the `except` branch, and prove only that the branch is reachable. It would say
nothing about the case that actually matters: Odoo cursors run REPEATABLE READ,
so a mapping COMMITTED by another session after this transaction's snapshot was
taken is refused by the index while remaining invisible to `search`. That is
the branch with nothing to compare against, and it is exactly where the old
implementation reported success and resumed the order.

So: a committed fixture on its own connection, a competing administrator on a
second connection with an asserted distinct backend PID, a real commit, and
then the production `action_confirm` meeting the real index. Bounded statement
and lock timeouts, because a proof about lock conflicts that is one deadlock
away from hanging the suite reports as neither pass nor fail. Committed rows
are removed and their absence asserted, because `TransactionCase` cannot roll
back what another connection committed.

THE DEFECT, EXACTLY
-------------------

`_create_mapping` caught the `IntegrityError`, searched for whatever row held
`UNIQUE(store_id, shopify_tax_evidence_key)`, and returned it as this call's
result. `action_confirm` then reported success and resumed the order -- under
a tax the administrator had not chosen and was never shown. An administrator
who deliberately picked one 5% tax could be told their decision was applied
while the order resumed under a different one, with the audit trail recording
the confirmation as having succeeded.

Zero Shopify contact: nothing in this file constructs a client, and the blocked
job is produced by the real `_resolve_taxes` refusal, which reaches no
transport at all.
"""

import json
import uuid

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from ..models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
)

STATEMENT_TIMEOUT_MS = 15000
LOCK_TIMEOUT_MS = 8000


def _open_bounded(dbname):
    """A real pooled cursor carrying both transaction-local PG limits.

    Bounded so this file fails closed. A proof about lock conflicts that is one
    deadlock away from hanging the suite reports as neither pass nor fail,
    which is the worst available outcome.
    """
    cr = db_connect(dbname).cursor()
    try:
        cr.execute(
            "SELECT set_config('statement_timeout', %s, true), "
            "set_config('lock_timeout', %s, true)",
            (str(STATEMENT_TIMEOUT_MS), str(LOCK_TIMEOUT_MS)),
        )
    except BaseException:
        cr.close()
        raise
    return cr


def _cleanup_committed_fixture(dbname, fixture):
    """Remove this test's COMMITTED rows, then prove they are gone.

    Registered with `addClassCleanup`, NOT `addCleanup`, and the difference is
    load-bearing. `TestCase` cleanups run LIFO, and `TransactionCase` registers
    its savepoint rollback in `setUp` -- so a cleanup registered from inside a
    test body runs FIRST, while the test transaction still holds the foreign-key
    share lock its job row took on the store. Deleting the store there blocks
    until `lock_timeout` and reports as an error in a test that had already
    passed. A class cleanup runs after the class cursor has been rolled back
    and closed, when nothing holds anything.
    """
    cr = _open_bounded(dbname)
    store_id = fixture['store_id']
    try:
        cr.execute(
            'DELETE FROM shopify_connector_job_log WHERE job_id IN '
            '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
            (store_id,),
        )
        for table in (
            'shopify_connector_tax_mapping',
            'shopify_connector_call_lease',
            'shopify_connector_job',
            'shopify_connector_store_settings',
            'shopify_connector_store_credential',
            'shopify_connector_store',
        ):
            column = 'id' if table == 'shopify_connector_store' else 'store_id'
            cr.execute(
                'DELETE FROM %s WHERE %s = %%s' % (table, column),
                (store_id,),
            )
        for tax_id in (fixture['mine_tax_id'], fixture['theirs_tax_id']):
            cr.execute('DELETE FROM account_tax WHERE id = %s', (tax_id,))
        cr.execute(
            'DELETE FROM res_partner WHERE id = %s', (fixture['partner_id'],),
        )
        cr.commit()
        cr.execute(
            'SELECT count(*) FROM shopify_connector_store WHERE id = %s',
            (store_id,),
        )
        remaining = cr.fetchone()[0]
        cr.execute(
            'SELECT count(*) FROM shopify_connector_tax_mapping '
            ' WHERE store_id = %s', (store_id,),
        )
        mappings = cr.fetchone()[0]
        assert not remaining and not mappings, (
            'the genuine-connection fixture left committed residue: '
            '%d store row(s), %d mapping row(s)' % (remaining, mappings)
        )
        cr.rollback()
    finally:
        cr.close()


@tagged('post_install', '-at_install', '-standard',
        'shopify_connector_tax_mapping_race')
class TestTaxMappingCompetingChoiceRace(TransactionCase):

    # -- genuine-connection harness ------------------------------------

    def _open_bounded(self):
        return _open_bounded(self.env.cr.dbname)

    def _backend_pid(self, cr):
        cr.execute('SELECT pg_backend_pid()')
        return cr.fetchone()[0]

    # -- committed fixture ---------------------------------------------

    def _commit_fixture(self):
        """A committed store, settings and two eligible taxes.

        Committed on its own connection, because both sides below must see it
        from transactions this one does not own. Every posture here is
        INHERITED from the company default rather than overridden -- the shape
        the F4 correction made reachable, and the shape a real merchant has.
        """
        suffix = uuid.uuid4().hex[:8]
        cr = self._open_bounded()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            company = env.company
            country = (
                company.account_fiscal_country_id
                or company.country_id
                or env.ref('base.us')
            )
            store = env['shopify.connector.store'].create({
                'name': 'Tax mapping race store %s' % suffix,
                'shop_domain': 'tax-race-%s.myshopify.com' % suffix,
                'api_version': self._api_version(),
                'company_id': company.id,
            })
            store.write({'state': 'connected'})
            partner = env['res.partner'].create({
                'name': 'Tax mapping race fallback %s' % suffix,
            })
            pricelist = env['product.pricelist'].search([
                ('active', '=', True),
                ('currency_id', '=', company.currency_id.id),
                '|', ('company_id', '=', False),
                ('company_id', '=', company.id),
            ], order='company_id desc, id', limit=1)
            if not pricelist:
                pricelist = env['product.pricelist'].create({
                    'name': 'Tax mapping race pricelist %s' % suffix,
                    'currency_id': company.currency_id.id,
                    'company_id': company.id,
                })
            payment_term = env.ref(
                'account.account_payment_term_immediate',
                raise_if_not_found=False,
            ) or env['account.payment.term'].create({
                'name': 'Tax mapping race term %s' % suffix,
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'sale_domain_enabled': True,
                'order_company_id': company.id,
                'order_pricelist_id': pricelist.id,
                'order_payment_term_id': payment_term.id,
                'customer_fallback_partner_id': partner.id,
            })
            taxes = []
            for label in ('mine', 'theirs'):
                group = env['account.tax.group'].create({
                    'name': 'Tax race %s %s' % (label, suffix),
                    'company_id': company.id,
                    'country_id': country.id,
                })
                tax = env['account.tax'].create({
                    'name': 'Tax race %s %s' % (label, suffix),
                    'amount': 5.0,
                    'amount_type': 'percent',
                    'type_tax_use': 'sale',
                    'company_id': company.id,
                    'country_id': country.id,
                    'tax_group_id': group.id,
                    'include_base_amount': False,
                })
                assert not tax.price_include_override
                taxes.append(tax.id)
            env.flush_all()
            fixture = {
                'store_id': store.id,
                'company_id': company.id,
                'partner_id': partner.id,
                'pricelist_id': pricelist.id,
                'payment_term_id': payment_term.id,
                'mine_tax_id': taxes[0],
                'theirs_tax_id': taxes[1],
            }
            cr.commit()
            self.addClassCleanup(
                _cleanup_committed_fixture, self.env.cr.dbname, fixture,
            )
        finally:
            cr.close()
        return fixture

    def _api_version(self):
        from odoo.addons.shopify_connector_core.tools.api_version import (
            SHOPIFY_API_VERSION,
        )
        return SHOPIFY_API_VERSION

    # -- the blocked job, through production code ----------------------

    def _block_on_unknown_tax(self, fixture):
        store = self.env['shopify.connector.store'].browse(
            fixture['store_id'],
        )
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        order = self.env['sale.order'].create({
            'partner_id': fixture['partner_id'],
            'company_id': fixture['company_id'],
            'pricelist_id': fixture['pricelist_id'],
            'payment_term_id': fixture['payment_term_id'],
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'res_model': 'shopify.connector.store',
            'res_id': store.id,
            'shopify_target_gid': 'gid://shopify/Order/8801234567',
            'expected_connection_generation': store.connection_generation,
        })
        evidence = {
            'title': 'VAT',
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }
        with self.assertRaises(JobHandlerError) as blocked:
            self.env['shopify.connector.order.importer']._resolve_taxes(
                order, store, [evidence], False, settings,
            )
        exc = blocked.exception
        self.env['shopify.connector.job.dispatch']._route_failure(
            job, exc.error_class, exc.reason, exc.technical_detail,
        )
        job.invalidate_recordset()
        return job, json.loads(exc.technical_detail)

    def _admin(self):
        return self.env['res.users'].sudo().create({
            'name': 'Tax mapping race admin',
            'login': 'tax_mapping_race_admin_%s' % uuid.uuid4().hex[:8],
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })

    def _commit_competing_mapping(self, fixture, fingerprint, tax_id):
        """A second administrator's mapping, on a second real connection."""
        cr = self._open_bounded()
        try:
            other_pid = self._backend_pid(cr)
            self.env.cr.execute('SELECT pg_backend_pid()')
            self.assertNotEqual(
                other_pid, self.env.cr.fetchone()[0],
                'the competing write must run on a genuinely different '
                'PostgreSQL backend, or this proves nothing about a race',
            )
            env = api.Environment(cr, SUPERUSER_ID, {})
            mapping = env['shopify.connector.tax.mapping'].create({
                'store_id': fixture['store_id'],
                'shopify_tax_evidence_key': fingerprint,
                'shopify_tax_fingerprint_version':
                    SHOPIFY_TAX_FINGERPRINT_VERSION,
                'shopify_price_included': False,
                'account_tax_id': tax_id,
            })
            env.flush_all()
            mapping_id = mapping.id
            cr.commit()
        finally:
            cr.close()
        return mapping_id

    # -- the proof -----------------------------------------------------

    def test_a_competing_choice_committed_elsewhere_refuses_and_never_resumes(self):
        fixture = self._commit_fixture()
        job, detail = self._block_on_unknown_tax(fixture)
        self.assertEqual(job.state, 'failed_retryable')

        admin = self._admin()
        action = job.with_user(admin).action_open_tax_mapping_decision()
        Wizard = self.env['shopify.connector.tax.decision.wizard'].with_user(
            admin
        ).with_context(**action['context'])
        values = dict(Wizard.default_get(list(Wizard._fields)))
        values['account_tax_id'] = fixture['mine_tax_id']
        wizard = Wizard.create(values)
        self.assertIn(
            fixture['mine_tax_id'], wizard.candidate_tax_ids.ids,
            'the inherited-posture tax was not even offered, so this test '
            'would be about the wrong thing',
        )

        # The other administrator wins, on their own connection, and COMMITS.
        winner_id = self._commit_competing_mapping(
            fixture, detail['fingerprint'], fixture['theirs_tax_id'],
        )
        self.assertTrue(winner_id)
        # REPEATABLE READ: this transaction's snapshot predates that commit,
        # so the winner is genuinely invisible here. That is the branch under
        # test, and asserting it makes the test say so rather than assume it.
        self.assertFalse(
            self.env['shopify.connector.tax.mapping'].sudo().search([
                ('store_id', '=', fixture['store_id']),
            ]),
            'the competing mapping is visible to this snapshot, so the '
            'nothing-to-compare-against branch is not what ran',
        )

        with self.assertRaises(UserError) as refused:
            wizard.action_confirm()
        self.assertIn('NOT applied', str(refused.exception))

        job.invalidate_recordset()
        self.assertEqual(
            job.state, 'failed_retryable',
            'the refused decision resumed the order anyway',
        )

        # Observed on a THIRD independent connection, so this is the committed
        # database rather than this transaction's opinion of it.
        cr = self._open_bounded()
        try:
            cr.execute(
                'SELECT id, account_tax_id FROM shopify_connector_tax_mapping '
                ' WHERE store_id = %s ORDER BY id',
                (fixture['store_id'],),
            )
            rows = cr.fetchall()
        finally:
            cr.rollback()
            cr.close()
        self.assertEqual(
            len(rows), 1,
            'the refused confirmation created a second mapping',
        )
        self.assertEqual(rows[0][0], winner_id)
        self.assertEqual(
            rows[0][1], fixture['theirs_tax_id'],
            'the refused administrator replaced the mapping that had won',
        )
