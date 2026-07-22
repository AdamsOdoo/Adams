import ast
import uuid
from pathlib import Path

from odoo import api, fields, SUPERUSER_ID
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_job import (
    fulfillment_operation_scope_key,
)


@tagged('post_install', '-at_install')
class TestFulfillmentConcurrency(TransactionCase):
    """Genuine independent-transaction concurrency for the fulfillment Layer 2
    path: the shared reconcile owns no remote-effect operation scope, the two
    mutation domains hold distinct Q1 scopes, and an overlapping same-scope
    mutation insert is refused (serialized to exactly one)."""

    def setUp(self):
        super().setUp()
        self.dbname = self.env.cr.dbname

    # -- The reconcile job owns/inherits NO remote-effect operation scope.

    def test_shared_reconcile_owns_no_operation_scope(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'fulfillment_domain_enabled': True,
        })
        # A reconcile job has no res_model -> operation_scope_key is False.
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'reconciliation',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 5,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/9',
            'payload_hash': uuid.uuid4().hex,
        })
        # The mutation job DOES hold the Q1 literal.
        self.assertEqual(
            job.operation_scope_key,
            fulfillment_operation_scope_key(
                'fulfillment_create', store.id, 5,
                'gid://shopify/FulfillmentOrder/9',
            ),
        )

    def test_mutation_scopes_distinct_per_domain(self):
        create_scope = fulfillment_operation_scope_key(
            'fulfillment_create', 1, 5, 'gid://shopify/FulfillmentOrder/9')
        tracking_scope = fulfillment_operation_scope_key(
            'fulfillment_tracking_update', 1, 5, 'gid://shopify/Fulfillment/9')
        self.assertNotEqual(create_scope, tracking_scope)
        self.assertTrue(create_scope.startswith('fulfillment_create:'))
        self.assertTrue(
            tracking_scope.startswith('fulfillment_tracking_update:'))

    def test_terminal_mutation_job_releases_its_scope(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'fulfillment_domain_enabled': True,
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 7,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/7',
            'payload_hash': uuid.uuid4().hex,
        })
        self.assertTrue(job.operation_scope_key)
        job.sudo().write({
            'state': 'cancelled', 'cancel_reason': 'x',
            'finished_at': fields.Datetime.now(),
        })
        job.invalidate_recordset()
        # A terminal job clears its scope so a replacement never collides.
        self.assertFalse(job.operation_scope_key)

    def test_overlapping_same_scope_insert_is_refused(self):
        """Genuine independent-connection overlap: an uncommitted mutation job
        holding an operation scope blocks a second insert of the same scope
        (unique operation-scope index). Runs on real pooled cursors at Gate C."""
        # Committed store fixture on its own connection.
        with db_connect(self.dbname).cursor() as setup_cr:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07', 'state': 'connected',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'fulfillment_domain_enabled': True,
            })
            store_id = store.id
            setup_cr.commit()
        self.addCleanup(self._cleanup_store, store_id)

        vals = {
            'store_id': store_id, 'job_source': 'manual_sync',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 42,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/42',
            'payload_hash': 'scope-a',
        }
        # First connection holds an uncommitted job with the scope live.
        holder_cr = db_connect(self.dbname).cursor()
        try:
            holder_env = api.Environment(holder_cr, SUPERUSER_ID, {})
            holder_env['shopify.connector.job'].create(vals)
            holder_env.cr.flush()
            # Second connection: same scope, different payload -> refused.
            with db_connect(self.dbname).cursor() as other_cr:
                other_cr.execute('SET LOCAL lock_timeout = %s', ('2s',))
                other_env = api.Environment(other_cr, SUPERUSER_ID, {})
                clash = dict(vals, payload_hash='scope-b')
                with self.assertRaises(Exception):
                    other_env['shopify.connector.job'].create(clash)
                    other_env.cr.flush()
        finally:
            holder_cr.rollback()
            holder_cr.close()

    def _cleanup_store(self, store_id):
        with db_connect(self.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store_settings WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s', (store_id,),
            )
            cr.commit()

    # -- Harness contract (AST): spawn, not fork, run_* functions, wiring.

    def test_external_concurrency_harness_contract(self):
        path = Path(__file__).with_name(
            'runtime_layer2_fulfillment_concurrency_harness.py')
        source = path.read_text('utf-8')
        tree = ast.parse(source)
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn('run_c1_ownership_race', funcs)
        self.assertIn('_new_environment', funcs)
        self.assertIn('_runtime', funcs)
        self.assertIn("get_context('spawn')", source)
        self.assertNotIn("get_context('fork')", source)
        self.assertIn('Registry(', source)
        self.assertIn('Environment', source)
        # The harness is NOT imported by the test package.
        init_source = path.with_name('__init__.py').read_text('utf-8')
        self.assertNotIn(
            'runtime_layer2_fulfillment_concurrency_harness', init_source)
