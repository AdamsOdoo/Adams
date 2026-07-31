"""Batch 2 §9 -- consolidated vertical journey I: administrator settings.

An administrator who configured a store during onboarding comes back to it
later, through the canonical Configuration -> Store Settings route, changes
one thing, and everything else stays exactly as it was.

WHY THE ROUTE MATTERS MORE THAN THE WRITE. Every assertion here goes through
`action_open_canonical_store_settings` -- the real menu action, with its
server-side role assertion, its ordinary-environment store resolution and its
row-ensure seam -- rather than reaching for the settings record directly. A
journey that started from `env['...store.settings'].search(...)` would prove
the model works while saying nothing about whether an administrator can get
to it.
"""

from lxml import etree
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

SETTINGS_MODEL = 'shopify.connector.store.settings'


@tagged('post_install', '-at_install')
class TestBatch2CoreJourneys(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Journey I Co A'})
        cls.other_company = cls.env['res.company'].create({
            'name': 'Journey I Co B',
        })
        cls.store = cls._make_store('journey-i-a', cls.company)
        cls.other_store = cls._make_store('journey-i-b', cls.other_company)
        cls.admin = cls._make_user(
            'admin', 'group_shopify_connector_admin', cls.company,
        )
        cls.operator = cls._make_user(
            'operator', 'group_shopify_connector_operator', cls.company,
        )
        cls.foreign_admin = cls._make_user(
            'foreign-admin', 'group_shopify_connector_admin',
            cls.other_company,
        )

    @classmethod
    def _make_store(cls, slug, company):
        return cls.env['shopify.connector.store'].create({
            'name': 'Journey I %s' % slug,
            'shop_domain': '%s.myshopify.com' % slug,
            'api_version': '2026-07',
            'company_id': company.id,
        })

    @classmethod
    def _make_user(cls, label, group_xmlid, company):
        return cls.env['res.users'].create({
            'name': 'Journey I %s' % label,
            'login': 'journey_i_%s' % label.replace('-', '_'),
            'group_ids': [
                (6, 0, [cls.env.ref(
                    'shopify_connector_core.%s' % group_xmlid,
                ).id]),
            ],
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
        })

    def _open_settings(self, user):
        """The production route in: the Configuration menu's own action."""
        return self.env[SETTINGS_MODEL].with_user(
            user
        ).action_open_canonical_store_settings()

    def _settings_of(self, store, user):
        return self.env[SETTINGS_MODEL].with_user(user).search([
            ('store_id', '=', store.id),
        ], limit=1)

    # ==================================================================
    # JOURNEY I
    # ==================================================================

    def test_journey_i_administrator_reopens_and_changes_one_setting(self):
        admin = self.admin

        # --- 1. Reopen the store's configuration -----------------------
        action = self._open_settings(admin)
        self.assertEqual(action['res_model'], SETTINGS_MODEL)
        settings = self._settings_of(self.store, admin)
        self.assertTrue(
            settings,
            'the canonical action must ensure the row it is about to show',
        )

        # Establish a starting shape across several domains, so "unrelated
        # settings are preserved" is a claim with something to preserve.
        settings.write({
            'product_domain_enabled': True,
            'sale_domain_enabled': True,
            'inventory_domain_enabled': False,
            'log_redaction_retention_days': 30,
        })
        settings.sudo().write({'setup_readiness_stale_since': False})
        settings.invalidate_recordset()
        self.assertFalse(settings.setup_readiness_stale_since)

        # --- 2. Change a safe, readiness-IRRELEVANT setting -------------
        settings.write({'log_redaction_retention_days': 45})
        settings.invalidate_recordset()
        self.assertEqual(settings.log_redaction_retention_days, 45)
        self.assertFalse(
            settings.setup_readiness_stale_since,
            'an unrelated setting must not invalidate a readiness check',
        )
        # ...and the unrelated domain settings are untouched.
        self.assertTrue(settings.product_domain_enabled)
        self.assertTrue(settings.sale_domain_enabled)
        self.assertFalse(settings.inventory_domain_enabled)

        # --- 3. Change a readiness-RELEVANT setting ---------------------
        settings.write({'inventory_domain_enabled': True})
        settings.invalidate_recordset()
        self.assertTrue(settings.inventory_domain_enabled)
        self.assertTrue(
            settings.setup_readiness_stale_since,
            'enabling a domain changes what readiness means and must mark it '
            'stale',
        )
        # Everything else still exactly as it was.
        self.assertEqual(settings.log_redaction_retention_days, 45)
        self.assertTrue(settings.product_domain_enabled)
        self.assertTrue(settings.sale_domain_enabled)

        # --- 4. A no-op write is not a change ---------------------------
        settings.sudo().write({'setup_readiness_stale_since': False})
        settings.invalidate_recordset()
        settings.write({'inventory_domain_enabled': True})
        settings.invalidate_recordset()
        self.assertFalse(
            settings.setup_readiness_stale_since,
            'writing the value that is already stored is not a change',
        )

        # --- 5. A protected/read-only change is refused -----------------
        # Stated precisely, because the imprecise version would be a claim
        # this surface does not support. `readonly=True` on an Odoo field is
        # a UI contract, NOT a server refusal: a direct `write()` still lands.
        # So the refusal asserted here is the one that genuinely exists -- the
        # ACL, which admits only an Administrator -- and the protection on the
        # two read-only fields is asserted as what it really is: they are
        # readonly on the model, and the canonical form either renders them
        # readonly or does not render them at all.
        with self.assertRaises(AccessError):
            settings.with_user(self.operator).write({
                'log_redaction_retention_days': 1,
            })
        model = self.env[SETTINGS_MODEL]
        self.assertTrue(model._fields['store_id'].readonly)
        self.assertTrue(model._fields['setup_completed_at'].readonly)
        form = self.env.ref(
            'shopify_connector_core.'
            'view_shopify_connector_store_settings_canonical_form'
        )
        arch = etree.fromstring(form.arch_db)
        store_nodes = arch.xpath("//field[@name='store_id']")
        self.assertTrue(
            store_nodes, 'the canonical form no longer shows the store at all'
        )
        for node in store_nodes:
            self.assertEqual(node.get('readonly'), '1')
        self.assertFalse(
            arch.xpath("//field[@name='setup_completed_at']"),
            'setup progress is internal and is rendered on no settings form',
        )
        settings.invalidate_recordset()
        self.assertEqual(settings.store_id, self.store)
        self.assertEqual(settings.log_redaction_retention_days, 45)

    def test_journey_i_an_operator_cannot_reach_the_configuration(self):
        """The menu gate is chrome; the server is the control.

        The row is ensured through the administrator FIRST. Without that, the
        operator's refusal leaves no settings row at all, and the write below
        would run on an empty recordset -- which never raises, so the test
        would pass while proving nothing.
        """
        self._open_settings(self.admin)
        settings = self._settings_of(self.store, self.admin)
        self.assertTrue(settings)
        with self.assertRaises(AccessError):
            self._open_settings(self.operator)
        with self.assertRaises(AccessError):
            settings.with_user(self.operator).write({
                'log_redaction_retention_days': 99,
            })

    def test_journey_i_an_administrator_sees_only_their_own_company_store(
        self,
    ):
        self._open_settings(self.admin)
        self._open_settings(self.foreign_admin)
        mine = self.env[SETTINGS_MODEL].with_user(self.admin).search([])
        theirs = self.env[SETTINGS_MODEL].with_user(
            self.foreign_admin
        ).search([])
        self.assertIn(self.store, mine.mapped('store_id'))
        self.assertNotIn(self.other_store, mine.mapped('store_id'))
        self.assertIn(self.other_store, theirs.mapped('store_id'))
        self.assertNotIn(self.store, theirs.mapped('store_id'))

    def test_journey_i_reopening_twice_creates_no_second_row(self):
        self._open_settings(self.admin)
        first = self._settings_of(self.store, self.admin)
        self._open_settings(self.admin)
        rows = self.env[SETTINGS_MODEL].sudo().search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows, first.sudo())

    def test_journey_i_the_one_row_per_store_guarantee_survives_the_route(
        self,
    ):
        """The canonical route creates rows through the ordinary create path,
        so `UNIQUE(store_id)` is still the authority -- asserted, because a
        seam that quietly bypassed it would look identical until the day two
        administrators opened Configuration at the same moment."""
        self._open_settings(self.admin)
        with self.assertRaises(IntegrityError), \
                mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env[SETTINGS_MODEL].sudo().create({
                'store_id': self.store.id,
            })
        rows = self.env[SETTINGS_MODEL].sudo().search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(rows), 1)
