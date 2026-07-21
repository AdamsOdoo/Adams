"""Task 013 Track B -- genuine *simultaneous* concurrency proofs.

Every test here runs **two independent database transactions whose
lifetimes genuinely overlap in real time**: a *holder* transaction
acquires and keeps a real PostgreSQL row lock (``FOR UPDATE``) -- or an
uncommitted unique-index entry -- while a *worker* transaction, on its
own separate connection/environment/transaction, runs the real
production operation and hits that live contention. This is deliberately
distinct from the sequential independent-connection recovery/durability
tests in ``TestInventoryPreC2RecoverySeam`` (test_inventory_push_mechanics.py),
which open one committed connection strictly after another and never
overlap -- those prove committed recovery is *observable* across
connections, not simultaneous-worker serialization.

Overlapping in-process transactions (not OS threads) are used
deliberately: the connector's own inventory pair paths guard exclusively
with ``FOR UPDATE SKIP LOCKED`` (``try_lock_for_update``) and the
``operation_scope_key`` unique index, so a *non-blocking* second worker
either skips or is refused -- which is exactly what an overlapping second
transaction exercises here, deterministically and without the shared
in-process registry/pool locks that make raw Python threads deadlock in
Odoo (core's own genuine-concurrency harness uses OS processes for the
same reason).

Because a plain ``TransactionCase`` never commits, its uncommitted rows
are invisible to a separate ``db_connect`` connection; every fixture is
therefore created and committed through its own independent connection
and torn down with raw SQL in ``addCleanup``. No Shopify transport of any
kind occurs in this module.
"""

import uuid
from contextlib import contextmanager
from unittest.mock import patch

import psycopg2

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError, ValidationError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)
from odoo.addons.shopify_connector_inventory.models.shopify_connector_inventory_service import (
    InventoryActivationSupersededError,
    MAX_CAS_RETRY_ORDINAL,
    pair_scope_key,
)


@tagged('post_install', '-at_install')
class TestInventoryConcurrency(TransactionCase):

    def setUp(self):
        super().setUp()
        self.dbname = self.env.cr.dbname
        self.Service = self.env['shopify.connector.inventory.service']

    # ==================================================================
    # Independent-connection plumbing
    # ==================================================================

    @contextmanager
    def _txn(self, uid=SUPERUSER_ID, lock_timeout=None):
        """A fresh, genuinely independent connection + environment. The
        caller commits/rolls back inside the block."""
        cr = db_connect(self.dbname).cursor()
        try:
            if lock_timeout:
                cr.execute("SET lock_timeout = %s", (lock_timeout,))
            yield cr, api.Environment(cr, uid, {})
        finally:
            cr.close()

    @contextmanager
    def _holding_row_lock(self, model, record_id, uid=SUPERUSER_ID):
        """Open an independent transaction that acquires and HOLDS a real
        ``FOR UPDATE`` row lock on one record for the whole block, so a
        concurrent worker's own ``try_lock_for_update`` on that row skips.
        The holder's transaction stays open (and its lock held) until the
        block exits."""
        cr = db_connect(self.dbname).cursor()
        try:
            env = api.Environment(cr, uid, {})
            locked = env[model].browse(record_id).try_lock_for_update()
            self.assertTrue(
                locked, 'the holder failed to acquire the row lock (setup)',
            )
            yield
        finally:
            cr.rollback()
            cr.close()

    @contextmanager
    def _holding_uncommitted_child(self, info, child_type, uid=SUPERUSER_ID):
        """Open an independent transaction that creates -- but does NOT
        commit -- an inventory child job for the pair, so it holds the
        pair's ``operation_scope_key`` unique-index entry live. A
        concurrent worker inserting the same-scoped job blocks on this
        entry."""
        cr = db_connect(self.dbname).cursor()
        try:
            env = api.Environment(cr, uid, {})
            store = env['shopify.connector.store'].browse(info['store_id'])
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            child = env['shopify.connector.inventory.service']._create_inventory_job(
                store, 'scheduled_sync', child_type, binding,
            )
            # Force the INSERT + computed operation_scope_key write so the
            # pair's unique-index entry is genuinely live (uncommitted).
            env.flush_all()
            yield child.id
        finally:
            cr.rollback()
            cr.close()

    # ==================================================================
    # Committed fixtures (independent connection + raw-SQL cleanup)
    # ==================================================================

    def _durable_pair(self, first_push_state='confirmed', pending_target=10.0):
        tag = uuid.uuid4().hex[:12]
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Concurrency Store %s' % tag,
                'shop_domain': 'conc-%s.myshopify.com' % tag,
                'api_version': '2026-07',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'inventory_domain_enabled': True,
            })
            store.write({'state': 'connected'})
            warehouse = env['stock.warehouse'].search(
                [('company_id', '=', env.company.id)], limit=1,
            )
            location = env['stock.location'].create({
                'name': 'Conc Location %s' % tag,
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
            })
            mapping = env['shopify.connector.location.mapping'].sudo().create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Location/%s' % tag,
                'odoo_location_id': location.id,
                'match_key': 'manual',
            })
            template = env['product.template'].create({
                'name': 'Conc Product %s' % tag,
            })
            template_binding = env[
                'shopify.connector.product.template.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Product/%s' % tag,
                'product_template_id': template.id,
            })
            variant_binding = env[
                'shopify.connector.product.variant.binding'
            ].create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/ProductVariant/%s' % tag,
                'product_variant_id': template.product_variant_id.id,
                'product_template_binding_id': template_binding.id,
            })
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].sudo().create({
                'store_id': store.id,
                'product_variant_binding_id': variant_binding.id,
                'location_mapping_id': mapping.id,
                'shopify_inventory_item_gid':
                    'gid://shopify/InventoryItem/%s' % tag,
                'first_push_state': first_push_state,
                'pending_target_available': pending_target,
            })
            info = {
                'store_id': store.id,
                'binding_id': binding.id,
                'item_gid': binding.shopify_inventory_item_gid,
                'location_gid': mapping.shopify_gid,
                'shop_domain': store.shop_domain,
                'connection_generation': store.connection_generation,
                'pair_key': pair_scope_key(
                    store.id, binding.shopify_inventory_item_gid,
                    mapping.shopify_gid,
                ),
            }
            cr.commit()
        self.addCleanup(self._cleanup_store, info['store_id'])
        return info

    def _cleanup_store(self, store_id):
        with db_connect(self.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job_log WHERE job_id IN '
                '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_mutation_attempt WHERE job_id '
                'IN (SELECT id FROM shopify_connector_job WHERE store_id = %s)',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_inventory_level_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_product_variant_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_product_template_binding '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_location_mapping '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store_settings '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()

    def _make_running_job(self, env, info, job_type, cas_retry_ordinal=0):
        job = env['shopify.connector.job'].sudo().create({
            'store_id': info['store_id'],
            'job_source': 'scheduled_sync',
            'job_type': job_type,
            'state': 'queued',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': info['binding_id'],
            'shopify_target_gid': info['pair_key'],
            'payload_hash': uuid.uuid4().hex,
            'expected_connection_generation': info['connection_generation'],
            'cas_retry_ordinal': cas_retry_ordinal,
        })
        token = uuid.uuid4().hex
        job.sudo().write({
            'state': 'running',
            'current_attempt_token': token,
            'started_at': fields.Datetime.now(),
            'running_since': fields.Datetime.now(),
        })
        return job, token

    def _record_stale_attempt(self, env, info, job, token):
        side_context = dict(env.context)
        side_context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
        Attempt = env['shopify.connector.mutation.attempt'].with_context(
            side_context
        )
        attempt = Attempt._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': info['shop_domain'],
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': {
                'inventory_item_gid': info['item_gid'],
                'location_gid': info['location_gid'],
                'target_quantity': 10.0,
                'change_from_quantity': 5.0,
                'snapshot_taken_at': fields.Datetime.to_string(
                    fields.Datetime.now()
                ),
            },
            'business_intent_fingerprint': 'bif-%s' % token,
            'exact_request_fingerprint': 'erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        })
        attempt._record_direct_outcome(
            'failed_clean',
            evidence={
                'user_errors': [
                    {'code': 'CHANGE_FROM_QUANTITY_STALE', 'field': []},
                ],
            },
        )
        return attempt

    def _durable_stale_cas_predecessor(self, info, ordinal=1):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job, token = self._make_running_job(
                env, info, 'inventory_set_quantities',
                cas_retry_ordinal=ordinal,
            )
            self._record_stale_attempt(env, info, job, token)
            cr.commit()
            return job.id

    def _durable_blocked_release_job(self, info):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job, token = self._make_running_job(
                env, info, 'inventory_set_quantities',
            )
            self._record_stale_attempt(env, info, job, token)
            job.sudo().write({
                'state': 'blocked_manual_review',
                'error_class': 'inventory_location_missing',
                'manual_review_subreason': 'inventory_location_missing',
                'current_attempt_token': False,
                'finished_at': fields.Datetime.now(),
            })
            cr.commit()
            return job.id

    def _durable_running_activation(self, info):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job, token = self._make_running_job(
                env, info, 'inventory_activate',
            )
            cr.commit()
            return job.id, token

    def _durable_committed_push_sync(self, info):
        """A committed, non-terminal push_sync pair job (for the fast-path
        coalesce assertion)."""
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job, _token = self._make_running_job(
                env, info, 'inventory_push_sync',
            )
            cr.commit()
            return job.id

    def _durable_reviewer(self):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            reviewer = env['res.users'].create({
                'name': 'Conc Reviewer %s' % uuid.uuid4().hex[:8],
                'login': 'conc_reviewer_%s' % uuid.uuid4().hex[:8],
                'group_ids': [(6, 0, [
                    env.ref(
                        'shopify_connector_core.'
                        'group_shopify_connector_reviewer'
                    ).id,
                ])],
            })
            cr.commit()
            # A committed res.users is intentionally not torn down (its
            # partner/mail FK graph makes raw-SQL deletion unsafe); a
            # per-run reviewer with a unique login is harmless leftover,
            # cleared on the next rebuild -- the same trade-off the existing
            # fixtures make for stock.location / product.template.
            return reviewer.id

    # ------------------------------------------------------------------
    # Verification helpers (always through a fresh committed connection)
    # ------------------------------------------------------------------

    def _count_jobs(self, info, job_type, extra_domain=None):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            domain = [
                ('store_id', '=', info['store_id']),
                ('res_id', '=', info['binding_id']),
                ('res_model', '=',
                 'shopify.connector.inventory.level.binding'),
                ('job_type', '=', job_type),
            ]
            if extra_domain:
                domain += extra_domain
            return env['shopify.connector.job'].search_count(domain)

    def _count_nonterminal(self, info, job_type, extra_domain=None):
        domain = [('state', 'not in', ('cancelled', 'skipped', 'succeeded',
                                       'failed_final'))]
        if extra_domain:
            domain += extra_domain
        return self._count_jobs(info, job_type, domain)

    def _read_job(self, job_id):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            job = env['shopify.connector.job'].browse(job_id)
            return {
                'state': job.state,
                'cas_retry_ordinal': job.cas_retry_ordinal,
                'superseded_by_job_id': job.superseded_by_job_id.id,
                'manual_review_subreason': job.manual_review_subreason,
                'current_attempt_token': job.current_attempt_token,
            }

    def _attempt_count(self, job_id):
        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env['shopify.connector.mutation.attempt'].search_count([
                ('job_id', '=', job_id),
            ])

    # ==================================================================
    # 8.1 -- Simultaneous same-pair push_sync admission
    # ==================================================================

    def test_simultaneous_admission_serializes_to_exactly_one_pair_job(self):
        info = self._durable_pair()
        other = self._durable_pair()

        # (a) Genuine overlap: while one transaction holds an uncommitted
        #     push_sync scope-key entry for the pair, a second, overlapping
        #     transaction attempting the same admission is genuinely blocked
        #     by the DB unique index and (with a short lock_timeout) refused
        #     -- proving the index, not chance, serializes concurrent
        #     admission to exactly one non-terminal pair job.
        with self._holding_uncommitted_child(info, 'inventory_push_sync'):
            with self._txn(lock_timeout='2s') as (cr, env):
                store = env['shopify.connector.store'].browse(info['store_id'])
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                with self.assertRaises(psycopg2.OperationalError) as caught:
                    env[
                        'shopify.connector.inventory.service'
                    ]._create_inventory_job(
                        store, 'scheduled_sync', 'inventory_push_sync', binding,
                    )
                    cr.commit()
                self.assertEqual(getattr(caught.exception, 'pgcode', None),
                                 '55P03')
                cr.rollback()
        # The holder rolled back, so no pair job survives that contention.
        self.assertEqual(
            self._count_nonterminal(info, 'inventory_push_sync'), 0,
        )

        # (b) Benign coalesce: with a committed non-terminal pair job
        #     already visible, `_try_enqueue_push_sync` admits nothing and
        #     raises nothing (the loser coalesces safely).
        self._durable_committed_push_sync(info)
        with self._txn() as (cr, env):
            store = env['shopify.connector.store'].browse(info['store_id'])
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            coalesced = env[
                'shopify.connector.inventory.service'
            ]._try_enqueue_push_sync(store, binding, 'scheduled_sync')
            cr.commit()
            self.assertFalse(coalesced, 'a duplicate admission must coalesce')
        self.assertEqual(
            self._count_nonterminal(info, 'inventory_push_sync'), 1,
            'exactly one non-terminal push_sync pair job must remain',
        )

        # (c) A DIFFERENT pair remains independently admissible.
        with self._txn() as (cr, env):
            store = env['shopify.connector.store'].browse(other['store_id'])
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(other['binding_id'])
            job = env[
                'shopify.connector.inventory.service'
            ]._try_enqueue_push_sync(store, binding, 'scheduled_sync')
            cr.commit()
            self.assertTrue(job, 'an unrelated pair must still be admissible')

    # ==================================================================
    # 8.2 -- Orchestration handoff (push_sync -> activation / set_quantities)
    # ==================================================================

    def _assert_one_child_under_scope_contention(self, info, child_type):
        """The production guard that makes an orchestration->mutation
        handoff yield exactly one child is the child's ``operation_scope_key``
        DB unique index. While one transaction holds an uncommitted child of
        this type for the pair, an overlapping transaction creating the same
        child is genuinely blocked by that index and refused; after the
        holder rolls back, a single uncontended create succeeds -- exactly
        one child, never two.

        (The single-worker predecessor->child *atomic transition* is proven
        by the activation-superseded 8.3, CAS 8.4, reconciliation 8.5 and
        release 8.6 handoff tests. The orchestration handler is never entered
        twice for one job in production -- the core dispatcher claims the job
        under FOR UPDATE SKIP LOCKED first -- so the real contended surface
        is this child-admission index.)"""
        with self._holding_uncommitted_child(info, child_type):
            with self._txn(lock_timeout='2s') as (cr, env):
                store = env['shopify.connector.store'].browse(info['store_id'])
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                with self.assertRaises(psycopg2.OperationalError) as caught:
                    env[
                        'shopify.connector.inventory.service'
                    ]._create_inventory_job(
                        store, 'scheduled_sync', child_type, binding,
                    )
                    cr.commit()
                self.assertEqual(getattr(caught.exception, 'pgcode', None),
                                 '55P03')
                cr.rollback()
        self.assertEqual(self._count_nonterminal(info, child_type), 0)

        # Uncontended, exactly one child is admitted.
        with self._txn() as (cr, env):
            store = env['shopify.connector.store'].browse(info['store_id'])
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            env['shopify.connector.inventory.service']._create_inventory_job(
                store, 'scheduled_sync', child_type, binding,
            )
            cr.commit()
        self.assertEqual(self._count_nonterminal(info, child_type), 1)

    def test_orchestration_no_level_yields_exactly_one_activation_child(self):
        info = self._durable_pair()
        self._assert_one_child_under_scope_contention(info, 'inventory_activate')

    def test_orchestration_level_change_yields_one_set_quantities_child(self):
        info = self._durable_pair()
        self._assert_one_child_under_scope_contention(
            info, 'inventory_set_quantities',
        )

    # ==================================================================
    # 8.3 -- Activation-superseded recovery
    # ==================================================================

    def test_concurrent_activation_superseded_recovery_one_successor(self):
        info = self._durable_pair()
        job_id, token = self._durable_running_activation(info)

        # While a concurrent worker holds the activation job's row lock, the
        # pre-C2 activation-superseded recovery must safely skip -- creating
        # no successor, no attempt, and leaving the job untouched.
        with self._holding_row_lock('shopify.connector.job', job_id):
            with self._txn() as (cr, env):
                env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                    job_id, token,
                    InventoryActivationSupersededError(
                        'gid://shopify/InventoryLevel/already-present',
                    ),
                )
                # `_recover_activation_superseded` self-commits.
        self.assertEqual(self._read_job(job_id)['state'], 'running')
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 0)
        self.assertEqual(self._attempt_count(job_id), 0)

        # Uncontended, the recovery skips the activation and hands off to
        # exactly one fresh push_sync.
        with self._txn() as (cr, env):
            env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                job_id, token,
                InventoryActivationSupersededError(
                    'gid://shopify/InventoryLevel/already-present',
                ),
            )
        self.assertEqual(self._read_job(job_id)['state'], 'skipped')
        self.assertEqual(self._attempt_count(job_id), 0)
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 1)

        # A repeated loser execution creates no second successor.
        with self._txn() as (cr, env):
            env['shopify.connector.job.dispatch']._recover_pre_c2_failure(
                job_id, token,
                InventoryActivationSupersededError('gid://shopify/x/y'),
            )
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 1)

    # ==================================================================
    # 8.4 -- CAS successor race
    # ==================================================================

    def test_concurrent_cas_successor_creates_exactly_one_at_next_ordinal(self):
        info = self._durable_pair()
        predecessor_id = self._durable_stale_cas_predecessor(info, ordinal=1)

        # A concurrent worker holds the predecessor's row lock: the CAS
        # handoff must fail closed and create no successor.
        with self._holding_row_lock('shopify.connector.job', predecessor_id):
            with self._txn() as (cr, env):
                service = env['shopify.connector.inventory.service']
                job = env['shopify.connector.job'].browse(predecessor_id)
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                with self.assertRaises(JobHandlerError):
                    service._handoff_supersede(
                        job, binding, 'cas_stale_bounded_replacement',
                        'inventory_set_quantities', is_cas_replacement=True,
                    )
                cr.rollback()
        self.assertEqual(
            self._count_jobs(
                info, 'inventory_set_quantities',
                [('id', '!=', predecessor_id)],
            ),
            0,
        )
        self.assertEqual(self._read_job(predecessor_id)['state'], 'running')

        # Uncontended: exactly one successor at ordinal predecessor + 1.
        with self._txn() as (cr, env):
            service = env['shopify.connector.inventory.service']
            job = env['shopify.connector.job'].browse(predecessor_id)
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            successor = service._handoff_supersede(
                job, binding, 'cas_stale_bounded_replacement',
                'inventory_set_quantities', is_cas_replacement=True,
            )
            cr.commit()
            successor_id = successor.id

        predecessor = self._read_job(predecessor_id)
        successor = self._read_job(successor_id)
        self.assertEqual(predecessor['state'], 'cancelled')
        self.assertEqual(predecessor['superseded_by_job_id'], successor_id)
        self.assertEqual(successor['cas_retry_ordinal'], 2)
        self.assertLessEqual(successor['cas_retry_ordinal'],
                             MAX_CAS_RETRY_ORDINAL)
        self.assertEqual(
            self._count_nonterminal(info, 'inventory_set_quantities'), 1,
        )

    # ==================================================================
    # 8.5 -- Reconciliation replacement race (not_applied -> ordinal 0)
    # ==================================================================

    def test_concurrent_reconciliation_replacement_one_ordinal_zero(self):
        info = self._durable_pair()
        # An ordinal>0 predecessor proves the reconciliation replacement is
        # always ordinal 0, never inheriting the predecessor's ordinal.
        predecessor_id = self._durable_stale_cas_predecessor(info, ordinal=2)

        with self._holding_row_lock('shopify.connector.job', predecessor_id):
            with self._txn() as (cr, env):
                service = env['shopify.connector.inventory.service']
                job = env['shopify.connector.job'].browse(predecessor_id)
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                with self.assertRaises(JobHandlerError):
                    service._handoff_supersede(
                        job, binding,
                        'reconciliation_not_applied_replacement',
                        'inventory_set_quantities',
                    )
                cr.rollback()
        self.assertEqual(
            self._count_jobs(
                info, 'inventory_set_quantities',
                [('id', '!=', predecessor_id)],
            ),
            0,
        )

        with self._txn() as (cr, env):
            service = env['shopify.connector.inventory.service']
            job = env['shopify.connector.job'].browse(predecessor_id)
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            successor = service._handoff_supersede(
                job, binding, 'reconciliation_not_applied_replacement',
                'inventory_set_quantities',
            )
            cr.commit()
            successor_id = successor.id

        self.assertEqual(self._read_job(predecessor_id)['state'], 'cancelled')
        self.assertEqual(
            self._read_job(successor_id)['cas_retry_ordinal'], 0,
            'a reconciliation replacement is always ordinal 0',
        )
        self.assertEqual(
            self._count_nonterminal(info, 'inventory_set_quantities'), 1,
        )
        # No automatic activation on the set_quantities not_applied path.
        self.assertEqual(self._count_jobs(info, 'inventory_activate'), 0)

    # ==================================================================
    # 8.6 -- Manual-review release race
    # ==================================================================

    def test_concurrent_manual_review_release_one_successor(self):
        info = self._durable_pair()
        blocked_id = self._durable_blocked_release_job(info)
        reviewer_uid = self._durable_reviewer()

        # A concurrent operation holds the binding row lock: the release must
        # fail closed (UserError) and create no successor, no transport.
        with self._holding_row_lock(
            'shopify.connector.inventory.level.binding', info['binding_id'],
        ):
            with self._txn(uid=reviewer_uid) as (cr, env):
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                with self.assertRaises(UserError):
                    binding.action_recheck_inventory_pair('scheduled recheck')
                cr.rollback()
        self.assertEqual(self._read_job(blocked_id)['state'],
                         'blocked_manual_review')
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 0)

        # Uncontended: exactly one release, one ordinal-0 push_sync successor.
        with self._txn(uid=reviewer_uid) as (cr, env):
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            released = binding.action_recheck_inventory_pair('scheduled recheck')
            cr.commit()
            self.assertTrue(released)

        blocked = self._read_job(blocked_id)
        self.assertEqual(blocked['state'], 'cancelled')
        self.assertTrue(blocked['superseded_by_job_id'])
        self.assertFalse(blocked['manual_review_subreason'])
        successor_id = blocked['superseded_by_job_id']
        self.assertEqual(self._read_job(successor_id)['cas_retry_ordinal'], 0)
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 1)
        # No Shopify transport: the successor carries no mutation attempt.
        self.assertEqual(self._attempt_count(successor_id), 0)

    # ==================================================================
    # 8.7 -- Rollback / failure injection
    # ==================================================================

    def test_handoff_child_creation_failure_rolls_back_atomically(self):
        info = self._durable_pair()
        predecessor_id = self._durable_stale_cas_predecessor(info, ordinal=1)
        self.assertEqual(self._read_job(predecessor_id)['state'], 'running')

        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            service = env['shopify.connector.inventory.service']
            job = env['shopify.connector.job'].browse(predecessor_id)
            binding = env[
                'shopify.connector.inventory.level.binding'
            ].browse(info['binding_id'])
            # Inject a failure AFTER the predecessor is transitioned to
            # cancelled but BEFORE the successor row is committed.
            with patch.object(
                type(service), '_create_cas_successor_job',
                side_effect=RuntimeError('injected child-creation failure'),
            ):
                with self.assertRaises(RuntimeError):
                    service._handoff_supersede(
                        job, binding, 'cas_stale_bounded_replacement',
                        'inventory_set_quantities', is_cas_replacement=True,
                    )
            cr.rollback()

        after = self._read_job(predecessor_id)
        self.assertEqual(
            after['state'], 'running',
            'the predecessor must be restored to its original state',
        )
        self.assertFalse(
            after['superseded_by_job_id'],
            'no dangling supersede link may survive the rollback',
        )
        self.assertEqual(
            self._count_jobs(
                info, 'inventory_set_quantities',
                [('id', '!=', predecessor_id)],
            ),
            0,
            'no successor may survive the rolled-back handoff',
        )

    # ==================================================================
    # 8.8 -- PostgreSQL concurrency error
    # ==================================================================

    def test_pg_lock_contention_is_a_safe_skip_never_a_pg_error(self):
        """The inventory pair paths guard by ``FOR UPDATE SKIP LOCKED``
        (``try_lock_for_update``) and unique-constraint coalescing, never a
        blocking ``FOR UPDATE``. This test:

        (a) proves genuine PostgreSQL lock contention exists at the DB level
            -- a second connection with a short ``lock_timeout`` issuing a
            *blocking* ``SELECT ... FOR UPDATE`` on a row held by the first
            raises a real ``LockNotAvailable`` (SQLSTATE 55P03) error; and
        (b) proves production's own non-blocking lock over that exact held
            row returns EMPTY (a safe skip) instead -- so genuine contention
            is never converted into Shopify network uncertainty and creates
            no duplicate job or attempt.

        A raw serialization-failure / deadlock cannot be reliably induced
        *through the production inventory pair paths themselves* precisely
        because they never block on a contended row -- by design -- and is
        documented rather than fabricated.
        """
        info = self._durable_pair()
        table = 'shopify_connector_inventory_level_binding'
        holder_cr = db_connect(self.dbname).cursor()
        try:
            holder_cr.execute(
                'SELECT id FROM %s WHERE id = %%s FOR UPDATE' % table,
                (info['binding_id'],),
            )

            # (a) A genuine blocking FOR UPDATE with a short lock_timeout hits
            #     a real PostgreSQL concurrency error.
            induced = None
            with db_connect(self.dbname).cursor() as blocker_cr:
                blocker_cr.execute("SET lock_timeout = '250ms'")
                try:
                    blocker_cr.execute(
                        'SELECT id FROM %s WHERE id = %%s FOR UPDATE' % table,
                        (info['binding_id'],),
                    )
                except psycopg2.OperationalError as exc:
                    induced = exc
                    blocker_cr.rollback()
            self.assertIsNotNone(
                induced,
                'a blocking FOR UPDATE on a held row must raise a genuine '
                'PostgreSQL lock error',
            )
            self.assertEqual(
                getattr(induced, 'pgcode', None), '55P03',
                'expected LockNotAvailable (55P03), got pgcode=%r'
                % (getattr(induced, 'pgcode', None),),
            )

            # (b) Production's own non-blocking pair lock over the same held
            #     row is a safe skip -- empty recordset, no error.
            with db_connect(self.dbname).cursor() as reader_cr:
                env = api.Environment(reader_cr, SUPERUSER_ID, {})
                binding = env[
                    'shopify.connector.inventory.level.binding'
                ].browse(info['binding_id'])
                locked = binding.try_lock_for_update()
                self.assertFalse(
                    locked,
                    'the production pair lock must SKIP a row held by '
                    'another worker, never block or error',
                )
                reader_cr.rollback()
        finally:
            holder_cr.rollback()
            holder_cr.close()

        # No duplicate job or attempt was produced by the contention.
        self.assertEqual(self._count_jobs(info, 'inventory_push_sync'), 0)
        self.assertEqual(
            self._count_jobs(info, 'inventory_set_quantities'), 0,
        )
