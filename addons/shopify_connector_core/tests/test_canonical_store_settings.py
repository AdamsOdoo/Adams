"""Batch 2 checkpoint 1 -- the canonical Store Settings surface (core).

Covers §6.2 (core field ownership), §6.6 (structural classification), §6.7
(action, menu and the row-ensure seam) and §6.8 (write and readiness
behaviour) for the fields and machinery core itself contributes. The domain
sections carry their own classification tests in their own modules.
"""

from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.canonical_settings_classification import (
    CANONICAL_ACTION_XMLID,
    CANONICAL_EDITABLE,
    CANONICAL_FORM_XMLID,
    CANONICAL_LIST_XMLID,
    CANONICAL_READONLY,
    INTERNAL_PROTECTED,
    OWNED_BY_SURFACE,
    SETTINGS_MODEL,
    assert_module_classification,
    canonical_form_field_nodes,
)

MODULE = 'shopify_connector_core'

# §6.2 and §6.6, as data. Every core-contributed settings field, by name, with
# the classification it carries and -- for the two that are deliberately NOT on
# the canonical form -- the named surface or the named reason.
CORE_CLASSIFICATION = {
    'store_id': (
        CANONICAL_READONLY,
        'Identity of the configured store; never re-pointed from a settings '
        'edit.',
    ),
    'company_id': (
        CANONICAL_READONLY,
        'Inherited from the owning store (SEC-3); never an independent '
        'selector.',
    ),
    'product_domain_enabled': (CANONICAL_EDITABLE, ''),
    'sale_domain_enabled': (CANONICAL_EDITABLE, ''),
    'inventory_domain_enabled': (CANONICAL_EDITABLE, ''),
    'fulfillment_domain_enabled': (CANONICAL_EDITABLE, ''),
    'log_redaction_retention_days': (CANONICAL_EDITABLE, ''),
    'product_first_sync_source': (
        CANONICAL_READONLY,
        'Onboarding direction decision; a post-onboarding switch is not '
        'authorized on this surface.',
    ),
    'notification_default_enabled': (
        CANONICAL_READONLY,
        'Opt-in stays on the guided setup consequence-confirmation route '
        '(`save_notification`, which refuses to enable without an explicit '
        'confirmation); this surface adds no second consent path.',
    ),
    'price_source_of_truth': (
        OWNED_BY_SURFACE,
        'Export Settings (action_shopify_connector_store_settings_export) is '
        'already authoritative for price ownership.',
    ),
    'setup_wizard_step_key': (
        INTERNAL_PROTECTED,
        'Setup semantic-step progress, written only by the setup service.',
    ),
    'setup_wizard_step': (
        INTERNAL_PROTECTED,
        'Display-only ordinal of the setup step key; never a navigation '
        'authority.',
    ),
    'setup_readiness_stale_since': (
        INTERNAL_PROTECTED,
        'Readiness staleness marker; derived from writes, never typed.',
    ),
    'setup_completed_at': (
        INTERNAL_PROTECTED,
        'Setup completion timestamp, written only by the setup service.',
    ),
    'setup_completed_uid': (
        INTERNAL_PROTECTED,
        'Setup completion actor, written only by the setup service.',
    ),
    'setup_last_rerun_at': (
        INTERNAL_PROTECTED,
        'Setup rerun timestamp, written only by the setup service.',
    ),
    'setup_last_rerun_uid': (
        INTERNAL_PROTECTED,
        'Setup rerun actor, written only by the setup service.',
    ),
}


@tagged('post_install', '-at_install')
class TestCanonicalStoreSettingsCore(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Canonical Co A'})
        cls.other_company = cls.env['res.company'].create({
            'name': 'Canonical Co B',
        })
        cls.store = cls._make_store('canonical-a', cls.company)
        cls.other_store = cls._make_store('canonical-b', cls.other_company)
        # Creating a store does NOT create its settings row -- which is
        # precisely why the canonical menu needs a row-ensure seam at all.
        # The fixtures that exercise write/readiness behaviour need the row
        # to exist; the seam's own tests delete it again first.
        for store in (cls.store, cls.other_store):
            cls.env[SETTINGS_MODEL].create({'store_id': store.id})
        cls.admin_user = cls._make_user(
            'admin', 'group_shopify_connector_admin', cls.company,
        )
        cls.operator_user = cls._make_user(
            'operator', 'group_shopify_connector_operator', cls.company,
        )

    @classmethod
    def _make_store(cls, slug, company):
        return cls.env['shopify.connector.store'].create({
            'name': 'Canonical Settings %s' % slug,
            'shop_domain': '%s.myshopify.com' % slug,
            'api_version': '2026-07',
            'company_id': company.id,
        })

    @classmethod
    def _make_user(cls, label, group_xmlid, company):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Canonical Settings %s' % label,
            'login': 'canonical_settings_%s' % label,
            'group_ids': [(6, 0, [group.id])],
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
        })

    def _settings_for(self, store):
        return self.env[SETTINGS_MODEL].search(
            [('store_id', '=', store.id)], limit=1,
        )

    # ------------------------------------------------------------------
    # §6.6 -- structural classification
    # ------------------------------------------------------------------

    def test_every_core_settings_field_is_classified(self):
        assert_module_classification(self, MODULE, CORE_CLASSIFICATION)

    def test_price_source_of_truth_is_not_on_the_canonical_form(self):
        """§6.2: Export Settings is already authoritative for it.

        Asserted separately from the classification sweep because this is the
        one core field the canonical surface must actively decline to own, and
        a reader should be able to find that as its own named statement.
        """
        self.assertNotIn(
            'price_source_of_truth', canonical_form_field_nodes(self.env),
        )
        export_form = self.env.ref(
            'shopify_connector_product_export.'
            'view_shopify_connector_store_settings_form_export',
            raise_if_not_found=False,
        )
        if export_form:
            self.assertIn('price_source_of_truth', export_form.arch)

    # ------------------------------------------------------------------
    # §6.7 -- action, views, menu
    # ------------------------------------------------------------------

    def test_action_binds_both_canonical_views_explicitly(self):
        action = self.env.ref(CANONICAL_ACTION_XMLID)
        bound = {view.view_mode: view.view_id for view in action.view_ids}
        self.assertEqual(
            bound.get('list'), self.env.ref(CANONICAL_LIST_XMLID),
            'The canonical action must bind its own list view; without '
            'view_ids Odoo falls back to name ordering across the four '
            'surfaces sharing this model.',
        )
        self.assertEqual(
            bound.get('form'), self.env.ref(CANONICAL_FORM_XMLID),
        )

    def test_action_is_restricted_to_the_administrator_group(self):
        action = self.env.ref(CANONICAL_ACTION_XMLID)
        self.assertIn(
            self.env.ref(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
            action.group_ids,
        )

    def test_canonical_views_refuse_create_and_delete(self):
        for xmlid in (CANONICAL_LIST_XMLID, CANONICAL_FORM_XMLID):
            arch = self.env.ref(xmlid).arch
            self.assertIn('create="false"', arch, xmlid)
            self.assertIn('delete="false"', arch, xmlid)

    def test_canonical_list_is_not_inline_editable(self):
        self.assertNotIn('editable=', self.env.ref(CANONICAL_LIST_XMLID).arch)

    def test_menu_opens_the_server_seam_and_is_administrator_gated(self):
        menu = self.env.ref(
            'shopify_connector_core.menu_shopify_connector_store_settings'
        )
        self.assertEqual(menu.action._name, 'ir.actions.server')
        self.assertEqual(
            menu.action,
            self.env.ref(
                'shopify_connector_core.'
                'action_shopify_connector_store_settings_open'
            ),
        )
        admin_group = self.env.ref(
            'shopify_connector_core.group_shopify_connector_admin'
        )
        self.assertIn(admin_group, menu.group_ids)
        self.assertIn(
            admin_group,
            self.env.ref(
                'shopify_connector_core.menu_shopify_connector_configuration'
            ).group_ids,
        )

    # ------------------------------------------------------------------
    # §6.7 / §11.1 -- the seam is authorized on the server
    # ------------------------------------------------------------------

    def test_non_administrator_direct_call_is_refused(self):
        """A hidden menu is not the control (§11.1).

        The Operator reaches this method by RPC without any menu having
        rendered, which is exactly the case a `groups=` attribute does not
        cover.
        """
        with self.assertRaises(AccessError):
            self.env[SETTINGS_MODEL].with_user(
                self.operator_user
            ).action_open_canonical_store_settings()

    def test_administrator_call_returns_the_canonical_window_action(self):
        result = self.env[SETTINGS_MODEL].with_user(
            self.admin_user
        ).action_open_canonical_store_settings()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], SETTINGS_MODEL)
        self.assertEqual(result['id'], self.env.ref(CANONICAL_ACTION_XMLID).id)

    def test_opening_ensures_exactly_one_row_and_is_idempotent(self):
        self._settings_for(self.store).unlink()
        self.assertFalse(self._settings_for(self.store))
        Settings = self.env[SETTINGS_MODEL].with_user(self.admin_user)
        Settings.action_open_canonical_store_settings()
        first = self._settings_for(self.store)
        self.assertEqual(len(first), 1)
        Settings.action_open_canonical_store_settings()
        again = self.env[SETTINGS_MODEL].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(again, first, 'The row ensure must be idempotent.')

    def test_row_ensure_never_reaches_a_foreign_company_store(self):
        """§6.7/§11.3: the authorized set is fixed BEFORE elevation.

        `sudo()` bypasses record rules outright, so the safety property being
        proved here is not "rules still apply under elevation" -- it is that
        the other company's store was never in the set handed to the elevated
        code, and elevation cannot widen it afterwards.
        """
        self._settings_for(self.other_store).unlink()
        self.env[SETTINGS_MODEL].with_user(
            self.admin_user
        ).action_open_canonical_store_settings()
        self.assertFalse(
            self._settings_for(self.other_store),
            'Opening Store Settings as a company-A administrator created a '
            'settings row for a company-B store.',
        )

    def test_widened_store_discovery_is_refused_not_silently_filtered(self):
        """The tripwire fires when resolution is widened (§6.7/§11.4).

        This reproduces the mistake directly rather than waiting for someone
        to make it: the store resolution is patched to return every store, as
        an elevated or context-forced search would. The seam must REFUSE.

        A silent `filtered()` here would pass this test while doing nothing,
        which is why the production code raises instead.
        """
        Store = self.env['shopify.connector.store']
        every_store = self.store | self.other_store
        with patch.object(
            type(Store), 'search',
            lambda records, *args, **kwargs: every_store.with_env(records.env),
        ):
            with self.assertRaises(AccessError):
                self.env[SETTINGS_MODEL].with_user(
                    self.admin_user
                ).action_open_canonical_store_settings()

    def test_a_company_less_store_is_never_configured(self):
        """Historic company-less stores are invisible by design.

        `store_company_rule` is `[('company_id', 'in', company_ids)]`, so a
        store awaiting the administrative company backfill is excluded from
        the ordinary search. The seam must not quietly adopt it either.
        """
        # `_check_company_assigned` refuses a company-less store through the
        # ORM, so this shape can only be reached the way it actually exists in
        # the wild: rows written before that constraint, which the SEC-3
        # backfill could not prove an owner for. Reproduced with SQL for the
        # same reason the constraint cannot be used -- the point is a row the
        # constraint would refuse today.
        orphan = self._make_store('canonical-orphan', self.company)
        self.env.cr.execute(
            'UPDATE shopify_connector_store SET company_id = NULL WHERE id = %s',
            (orphan.id,),
        )
        self.env.invalidate_all()
        self.assertFalse(orphan.company_id)
        self.env[SETTINGS_MODEL].with_user(
            self.admin_user
        ).action_open_canonical_store_settings()
        self.assertFalse(self._settings_for(orphan))

    def test_row_ensure_contains_a_concurrent_unique_row_winner(self):
        """The `UNIQUE(store_id)` violation is contained, not raised.

        Patching the pre-check to see nothing reproduces the interleaving
        where another opener committed its row between our search and our
        create. The production path must absorb that and leave one row.
        """
        Settings = self.env[SETTINGS_MODEL]
        existing = self._settings_for(self.store)
        self.assertTrue(existing)
        with patch.object(
            type(Settings), 'search',
            lambda records, *args, **kwargs: records.browse(),
        ):
            Settings._ensure_canonical_settings_rows(self.store)
        rows = Settings.search([('store_id', '=', self.store.id)])
        self.assertEqual(
            rows, existing,
            'A losing concurrent create must leave the winner untouched.',
        )

    # ------------------------------------------------------------------
    # §6.8 -- readiness staleness
    # ------------------------------------------------------------------

    def test_readiness_relevant_fields_follow_the_readiness_registry(self):
        """Core declares what core's readiness checks actually consume.

        Derived from `_accepted_domain_flags()` rather than copied beside it,
        so an installed domain that registers its own sync-domain flag (Product
        Export does) is covered without editing this file.
        """
        declared = self.env[SETTINGS_MODEL]._readiness_relevant_fields()
        accepted = set(
            self.env['shopify.connector.readiness.check']
            ._accepted_domain_flags()
        )
        self.assertEqual(declared, accepted)
        self.assertIn('sale_domain_enabled', declared)

    def test_a_meaningful_change_marks_readiness_stale(self):
        settings = self._settings_for(self.store)
        settings._clear_setup_readiness_stale()
        self.assertFalse(settings.setup_readiness_stale_since)
        settings.write({
            'sale_domain_enabled': not settings.sale_domain_enabled,
        })
        self.assertTrue(
            settings.setup_readiness_stale_since,
            'Enabling a sync domain changes what readiness is a decision '
            'about, so the existing evidence must be marked stale.',
        )

    def test_a_no_op_write_does_not_mark_readiness_stale(self):
        settings = self._settings_for(self.store)
        settings.write({'sale_domain_enabled': True})
        settings._clear_setup_readiness_stale()
        settings.write({'sale_domain_enabled': True})
        self.assertFalse(
            settings.setup_readiness_stale_since,
            'Re-asserting the value already stored is not a configuration '
            'change and must not invalidate good readiness evidence.',
        )

    def test_an_unrelated_setting_does_not_mark_readiness_stale(self):
        """A canonical-editable field no readiness check reads (§6.8).

        `log_redaction_retention_days` is a real decision an Administrator
        takes here, and no readiness check consumes it -- so changing it must
        leave readiness evidence alone.
        """
        settings = self._settings_for(self.store)
        settings._clear_setup_readiness_stale()
        settings.write({'log_redaction_retention_days': 365})
        self.assertEqual(settings.log_redaction_retention_days, 365)
        self.assertFalse(settings.setup_readiness_stale_since)

    def test_writing_the_stale_marker_does_not_recurse(self):
        """Termination is a property of the field partition, not a guard.

        `setup_readiness_stale_since` is not readiness-relevant, so the nested
        write computes an empty changed-set and stops. If that ever stopped
        being true this would recurse until Python gave up.
        """
        settings = self._settings_for(self.store)
        settings._mark_setup_readiness_stale()
        first = settings.setup_readiness_stale_since
        self.assertTrue(first)
        settings.write({'setup_readiness_stale_since': False})
        self.assertFalse(settings.setup_readiness_stale_since)

    def test_existing_constraints_stay_load_bearing_on_the_form_path(self):
        """§6.8: the form saves through the ordinary write path.

        The unique-row guard is the one every canonical opener depends on, so
        it is asserted directly rather than assumed.
        """
        settings = self._settings_for(self.store)
        self.assertTrue(settings)
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env[SETTINGS_MODEL].sudo().create({
                    'store_id': self.store.id,
                })
