"""U1 acceptance A23 -- SEC-3 closure for the U1 surface.

Two obligations, both PROVEN rather than asserted:

1. U1 introduces NO new durable store-scoped model and NO new
   connector-to-connector relation. This is proven against the live registry via
   the same inventory the SEC-3 completeness guard uses, so a future U1 edit that
   adds one fails here.
2. Cross-company and quarantined rows are absent from every U1 read shape, while
   the owning company's user still sees the same row.
"""

import importlib.util
from pathlib import Path
import uuid

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tests.test_sec3_store_ownership import (
    TestSec3InventoryCompleteness,
)

USER_ROLE = 'shopify_connector_core.group_shopify_connector_user'

# Every model a U1 screen reads. Each must already be store-rooted by the merged
# SEC-3 work; U1 adds none of its own.
U1_VISIBLE_MODELS = (
    'shopify.connector.fulfillment.inbound.evidence',
    'shopify.connector.fulfillment.inbound.evidence.line',
    'shopify.connector.fulfillment.binding',
    'shopify.connector.store.settings',
    'shopify.connector.job',
)

# The two transient models U1 adds. A TransientModel is not durable storage: it
# is vacuumed, holds no business record, and is therefore outside the SEC-3
# store-scoped inventory by construction.
U1_NEW_MODELS = (
    'shopify.connector.fulfillment.mode.switch.wizard',
    'shopify.connector.fulfillment.review.release.wizard',
)


@tagged('post_install', '-at_install')
class TestUiSec3Scope(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'U1 Co A'})
        cls.company_b = cls.env['res.company'].create({'name': 'U1 Co B'})
        cls.store_a = cls.env['shopify.connector.store'].create({
            'name': 'U1 store A', 'company_id': cls.company_a.id,
            'shop_domain': 'u1a-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.store_b = cls.env['shopify.connector.store'].create({
            'name': 'U1 store B', 'company_id': cls.company_b.id,
            'shop_domain': 'u1b-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        base = cls.env.ref('base.group_user').id
        role = cls.env.ref(USER_ROLE).id
        cls.user_a = cls.env['res.users'].create({
            'name': 'U1 user A', 'login': 'u1sec_a_%s' % uuid.uuid4().hex,
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [base, role])],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'U1 user B', 'login': 'u1sec_b_%s' % uuid.uuid4().hex,
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(6, 0, [base, role])],
        })
        cls.evidence_a = cls.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo().create({
            'store_id': cls.store_a.id,
            'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/%s' % uuid.uuid4().hex,
            'origin_class': 'external_merchant',
            'reconciled_state': 'review',
            'review_reason': 'external_fulfillment_observed',
        })

    # ------------------------------------------------- obligation 1: no new surface

    def test_u1_adds_no_new_durable_store_scoped_model(self):
        for model_name in U1_NEW_MODELS:
            model = self.env[model_name]
            self.assertTrue(
                model._transient,
                '%s must be transient -- a durable model would have to join '
                'the SEC-3 store-scoped inventory.' % model_name,
            )
            # A transient MAY expose a related store_id for display -- that is
            # a projection of its target's store, not durable ownership. What
            # must not exist is a STORED column, which is what SEC-3's
            # store-rooted inventory and record rules are built on.
            store_field = model._fields.get('store_id')
            if store_field is not None:
                self.assertTrue(
                    store_field.related and not store_field.store,
                    '%s.store_id must be a non-stored related field, not '
                    'durable ownership.' % model_name,
                )

    def test_the_sec3_inventory_guard_does_not_pick_up_any_u1_model(self):
        """A23 proven by the authoritative guard, not by a local re-statement.

        `TestSec3InventoryCompleteness._durable_store_scoped_models` IS the
        discovery the SEC-3 completeness matrix runs against the live registry.
        Reusing it means U1 cannot drift from SEC-3's own definition of
        "durable store-scoped model": if a future U1 edit makes one, that
        function finds it and this fails.
        """
        durable = TestSec3InventoryCompleteness._durable_store_scoped_models(self)
        self.assertTrue(
            durable,
            'The discovery returned nothing, so this test would prove nothing.',
        )
        for model_name in U1_NEW_MODELS:
            self.assertNotIn(
                model_name, durable,
                '%s was picked up as a durable store-scoped model. U1 must add '
                'none, or it owes SEC-3 a row builder, a company field and a '
                'fail-closed rule.' % model_name,
            )
        # And every model U1 READS is already inside that inventory.
        for model_name in U1_VISIBLE_MODELS:
            if model_name == 'shopify.connector.store.settings':
                continue  # 1:1 with its store; covered via the store root
            self.assertIn(
                model_name, durable,
                '%s is read by U1 and must be under SEC-3 ownership.' % model_name,
            )

    def test_u1_adds_no_connector_to_connector_relation(self):
        """A wizard may POINT at a connector record (that is how it delegates),
        but only through a transient, vacuumed row -- never a durable edge."""
        for model_name in U1_NEW_MODELS:
            model = self.env[model_name]
            for name, field in model._fields.items():
                if field.type in ('many2one', 'one2many', 'many2many'):
                    self.assertTrue(
                        model._transient,
                        'Durable relation %s.%s would need SEC-3 coverage.'
                        % (model_name, name),
                    )

    def test_every_u1_visible_model_is_already_sec3_covered(self):
        """Company ownership is required of every U1-visible model.

        The quarantine flag is required only of models that can actually go
        out of scope, i.e. those carrying a connector-to-connector parent whose
        store could differ. `shopify.connector.store.settings` is 1:1 with its
        store and derives company_id from it, so it has no second parent to
        disagree with and nothing to quarantine -- requiring the flag there
        would be cargo-culting the mechanism past the risk it exists for.
        """
        quarantinable = []
        for model_name in U1_VISIBLE_MODELS:
            model = self.env[model_name]
            self.assertIn(
                'company_id', model._fields,
                '%s is read by a U1 screen and must carry company_id.' % model_name,
            )
            if hasattr(model, '_sec3_parent_scope_relations'):
                quarantinable.append(model_name)
                self.assertIn(
                    'sec3_scope_quarantined', model._fields,
                    '%s declares connector parents and must carry the '
                    'quarantine flag.' % model_name,
                )
        self.assertTrue(
            quarantinable,
            'At least one U1-visible model must be quarantinable, or this '
            'test proves nothing.',
        )

    # ------------------------------------- obligation 2: read shapes are scoped

    def test_owning_company_sees_the_row_and_the_other_does_not(self):
        Evidence = self.env['shopify.connector.fulfillment.inbound.evidence']
        seen_by_a = Evidence.with_user(self.user_a).search([
            ('id', '=', self.evidence_a.id),
        ])
        self.assertEqual(
            seen_by_a.ids, self.evidence_a.ids,
            'The owning company must still see its own row -- otherwise the '
            'negative assertion below would pass vacuously.',
        )
        seen_by_b = Evidence.with_user(self.user_b).search([
            ('id', '=', self.evidence_a.id),
        ])
        self.assertFalse(
            seen_by_b,
            'Company B must not see company A fulfillment evidence.',
        )

    def test_evidence_company_rule_xml_ids_have_one_canonical_declaration(self):
        addon = Path(__file__).resolve().parents[1]
        security_sources = ''.join(
            path.read_text(encoding='utf-8')
            for path in sorted((addon / 'security').glob('*.xml'))
        )
        for local_id in (
            'fulfillment_inbound_evidence_company_rule',
            'fulfillment_inbound_evidence_line_company_rule',
        ):
            self.assertEqual(
                security_sources.count('id="%s"' % local_id),
                1,
                '%s must have exactly one XML owner.' % local_id,
            )

    def test_evidence_company_rule_migration_repairs_noupdate_idempotently(self):
        path = (
            Path(__file__).resolve().parents[1]
            / 'migrations' / '19.0.1.11.0' / 'post-migrate.py'
        )
        spec = importlib.util.spec_from_file_location(
            'fulfillment_company_rule_migration', path,
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        Imd = self.env['ir.model.data'].sudo()
        for local_id, target in migration.RULES.items():
            rule = self.env.ref(
                'shopify_connector_fulfillment.%s' % local_id,
            ).sudo()
            rule.write({
                'name': 'Legacy permissive rule',
                'domain_force': "[(1, '=', 1)]",
            })
            metadata = Imd.search([
                ('module', '=', 'shopify_connector_fulfillment'),
                ('name', '=', local_id),
            ])
            self.assertEqual(len(metadata), 1)
            metadata.write({'noupdate': True})

        migration.migrate(self.env.cr, '19.0.1.10.0')
        first = {}
        for local_id, target in migration.RULES.items():
            rule = self.env.ref(
                'shopify_connector_fulfillment.%s' % local_id,
            ).sudo()
            metadata = Imd.search([
                ('module', '=', 'shopify_connector_fulfillment'),
                ('name', '=', local_id),
            ])
            self.assertEqual(rule.model_id.model, target['model'])
            self.assertEqual(rule.name, target['name'])
            self.assertEqual(rule.domain_force, target['domain_force'])
            self.assertTrue(rule.active)
            self.assertTrue(rule['global'])
            self.assertFalse(metadata.noupdate)
            first[local_id] = (rule.write_date, metadata.write_date)

        migration.migrate(self.env.cr, '19.0.1.11.0')
        for local_id in migration.RULES:
            rule = self.env.ref(
                'shopify_connector_fulfillment.%s' % local_id,
            ).sudo()
            metadata = Imd.search([
                ('module', '=', 'shopify_connector_fulfillment'),
                ('name', '=', local_id),
            ])
            self.assertEqual(first[local_id], (rule.write_date, metadata.write_date))

    def test_quarantined_rows_are_absent_from_every_u1_read_shape(self):
        self.env.cr.execute(
            'UPDATE shopify_connector_fulfillment_inbound_evidence '
            'SET sec3_scope_quarantined = TRUE WHERE id = %s',
            (self.evidence_a.id,),
        )
        self.env['shopify.connector.fulfillment.inbound.evidence'].invalidate_model(
            ['sec3_scope_quarantined'],
        )
        Evidence = self.env['shopify.connector.fulfillment.inbound.evidence'].with_user(
            self.user_a,
        )
        # The U1 list read shape.
        self.assertFalse(
            Evidence.search([('id', '=', self.evidence_a.id)]),
            'A quarantined row must not appear in the U1 list.',
        )
        # The U1 count read shape -- this is why no U1 count is authoritative.
        self.assertEqual(
            Evidence.search_count([('id', '=', self.evidence_a.id)]), 0,
        )
        # The U1 grouped/facet read shape.
        grouped = Evidence._read_group(
            [('id', '=', self.evidence_a.id)], groupby=['reconciled_state'],
            aggregates=['__count'],
        )
        self.assertFalse(grouped, 'A quarantined row must not appear in a facet.')

    def test_wizard_counts_respect_the_scope_rules(self):
        """The mode-switch wizard reads without sudo, so its counts inherit the
        same fail-closed rules -- which is exactly why they are labelled
        non-authoritative in the view."""
        settings_a = self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': self.store_a.id, 'fulfillment_domain_enabled': True,
        })
        admin = self.env['res.users'].create({
            'name': 'U1 admin A', 'login': 'u1sec_adm_%s' % uuid.uuid4().hex,
            'company_id': self.company_a.id,
            'company_ids': [(6, 0, [self.company_a.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin').id,
            ])],
        })
        wizard = self.env[
            'shopify.connector.fulfillment.mode.switch.wizard'
        ].with_user(admin).with_context(
            default_settings_id=settings_a.id,
        ).create({'settings_id': settings_a.id})
        self.assertEqual(
            wizard.open_review_count, 1,
            'The owning company sees its own open review case.',
        )
        self.env.cr.execute(
            'UPDATE shopify_connector_fulfillment_inbound_evidence '
            'SET sec3_scope_quarantined = TRUE WHERE id = %s',
            (self.evidence_a.id,),
        )
        self.env['shopify.connector.fulfillment.inbound.evidence'].invalidate_model(
            ['sec3_scope_quarantined'],
        )
        wizard2 = self.env[
            'shopify.connector.fulfillment.mode.switch.wizard'
        ].with_user(admin).with_context(
            default_settings_id=settings_a.id,
        ).create({'settings_id': settings_a.id})
        self.assertEqual(
            wizard2.open_review_count, 0,
            'A quarantined row must drop out of the wizard count too -- the '
            'count is therefore never a complete count.',
        )
