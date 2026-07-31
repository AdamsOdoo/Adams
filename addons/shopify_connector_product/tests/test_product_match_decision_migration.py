"""Batch 2 correction: the `v1` -> `v2` product-decision identity transition.

WHY THIS FILE EXISTS. The correction changes stored decision state: the
identity scheme behind `decision_key`, the evidence schema name, and the
column that carried the match values. A database that already holds decisions
written under the old scheme must not be left with rows that LOOK actionable
and cannot act, and must not have its already-consumed history rewritten.
Migration `19.0.2.8.0` is the answer, and this is the proof that it does what
it says on rows shaped exactly like the ones it will meet.

WHY THE MIGRATION IS A SUPERSESSION RATHER THAN A REPAIR. `v1` stored the
Shopify GIDs and the remote `updatedAt` after passing them through
`safe_match_preview`, whose phone pattern rewrites any run of seven or more
digits -- so `gid://shopify/Product/7346299043911` became
`gid://shopify/Product/[redacted-phone]`. That is not invertible, the original
digits are nowhere in the database, and two different products could produce
the same stored identity. "Pick the plausible one" is not a repair; it is a
coin toss that can bind a store's catalog to the wrong master data.
"""

import json
import uuid

from odoo.tests.common import TransactionCase, tagged

TABLE = 'shopify_connector_product_match_decision'


def _load_migration():
    """Import the migration by path.

    Odoo migration directories are version numbers, so they are not importable
    package names and `import` cannot reach them. This is the same reason
    Odoo's own loader reads them with `importlib` machinery.
    """
    import importlib.util
    from pathlib import Path
    path = (
        Path(__file__).resolve().parent.parent
        / 'migrations' / '19.0.2.8.0' / 'post-migrate.py'
    )
    spec = importlib.util.spec_from_file_location(
        'shopify_product_match_v2_migration', path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged('post_install', '-at_install')
class TestProductMatchDecisionV2Migration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = _load_migration()
        cls.Decision = cls.env['shopify.connector.product.match.decision']
        cls.store = cls.env['shopify.connector.store'].sudo().create({
            'name': 'Match migration store',
            'shop_domain': 'match-migration.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
            'company_id': cls.env.company.id,
        })
        cls.env['shopify.connector.store.settings'].sudo().create({
            'store_id': cls.store.id,
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })

    def _job(self):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'blocked_manual_review',
            'error_class': 'ambiguous_match',
            'manual_review_subreason': 'ambiguous_match',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': 'gid://shopify/Product/%s' % uuid.uuid4().hex,
        })

    def _legacy_decision(self, state, key_prefix='v1:'):
        """A row exactly as `v1` wrote it: MANGLED identity, `v1` key.

        Written with `sudo().create` because that is what the dispatcher seam
        did; the point is that the row is indistinguishable from a real one
        except for the two things the correction changed.
        """
        decision = self.Decision.sudo().create({
            'store_id': self.store.id,
            'job_id': self._job().id,
            'decision_level': 'template',
            # The identity as `v1` actually stored it.
            'shopify_product_gid': 'gid://shopify/Product/[redacted-phone]',
            'remote_updated_at': '2026-07-30T09:15:00Z',
            'decision_key': '%s%s' % (key_prefix, uuid.uuid4().hex * 2),
            'match_key': 'sku_reference',
            'match_value_digests': json.dumps([]),
        })
        if state != 'pending':
            decision.sudo().write({'state': state})
        self.env.flush_all()
        return decision

    def _run(self):
        self.env.flush_all()
        self.migration.migrate(self.env.cr, '19.0.2.7.0')
        self.env.invalidate_all()

    def test_undecided_v1_rows_are_retired_rather_than_reinterpreted(self):
        pending = self._legacy_decision('pending')
        confirmed = self._legacy_decision('confirmed')
        self._run()
        for decision in (pending, confirmed):
            self.assertEqual(
                decision.state, 'superseded',
                'a v1 decision that can never be consumed was left looking '
                'actionable',
            )
            self.assertIn('v1 identity rules', decision.superseded_reason)
            self.assertIn('cannot be recovered', decision.superseded_reason)
        # The identity was NOT rewritten into something plausible.
        self.assertEqual(
            pending.shopify_product_gid,
            'gid://shopify/Product/[redacted-phone]',
        )

    def test_a_consumed_v1_row_and_its_history_are_left_alone(self):
        """A consumed decision already produced a binding, and that binding is
        independently valid. Rewriting the decision would falsify the audit
        trail of a correct outcome."""
        consumed = self._legacy_decision('consumed')
        before = consumed.read()[0]
        self._run()
        self.assertEqual(consumed.state, 'consumed')
        self.assertFalse(consumed.superseded_reason)
        self.assertEqual(consumed.read()[0], before)

    def test_a_v2_row_is_not_touched(self):
        current = self._legacy_decision('pending', key_prefix='v2:')
        self._run()
        self.assertEqual(current.state, 'pending')
        self.assertFalse(current.superseded_reason)

    def test_the_migration_is_idempotent(self):
        pending = self._legacy_decision('pending')
        self._run()
        self.assertEqual(pending.state, 'superseded')
        first_reason = pending.superseded_reason
        self._run()
        self.assertEqual(pending.state, 'superseded')
        self.assertEqual(pending.superseded_reason, first_reason)

    def test_the_obsolete_match_values_column_is_gone(self):
        """The `v1` column held display-sanitized identifier copies. It must
        not survive as a second, wrong answer to "what did Shopify send?"."""
        self.env.cr.execute(
            'SELECT 1 FROM information_schema.columns '
            ' WHERE table_name = %s AND column_name = %s',
            (TABLE, 'match_values'),
        )
        self.assertIsNone(
            self.env.cr.fetchone(),
            'the obsolete match_values column is still present',
        )
        # ...and the migration drops it when it IS present, which is the case
        # an upgraded database actually presents.
        self.env.cr.execute(
            'ALTER TABLE %s ADD COLUMN match_values text' % TABLE
        )
        self._run()
        self.env.cr.execute(
            'SELECT 1 FROM information_schema.columns '
            ' WHERE table_name = %s AND column_name = %s',
            (TABLE, 'match_values'),
        )
        self.assertIsNone(self.env.cr.fetchone())

    def test_the_migration_survives_a_database_without_the_table(self):
        """`_record_from_failure` runs in every database where the product
        module is installed, but a migration must not assume the table it
        names exists -- the guard is the reason it can run at any point in a
        multi-module upgrade."""
        self.assertFalse(
            self.migration._table_exists(self.env.cr, 'no_such_table_at_all'),
        )
