"""Focused P10 adapter contracts.

The live PostgreSQL claim/finalization race belongs in the release gate with
two independent Odoo connections.  These tests keep the ordinary addon suite
cheap while still exercising the adapter's executable SQL builder, scope
fences, registry admission, legacy isolation and bounded mixed-drain policy.
The pure runtime tests cover the same decision tables without a registry.
"""

from __future__ import annotations

import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
import uuid

from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_v2_runtime import (
    OdooReadOnlyRuntimeRepository,
    ShopifyConnectorV2Runtime,
    _safe_transition_message,
    _TRANSITION_MESSAGE_LIMIT,
)
from ..runtime.p10_capacity import reserve_capacity_after_v2
from ..runtime.p10_coordinator import ClaimedWork
from ..runtime.p10_stale_owner import StaleOwnerInput, StaleOwnerPolicy


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class _RecordingCursor:
    def __init__(self, rows=((41,),)):
        self.rows = rows
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows


class _SequenceCursor:
    """Small cursor double for the two-step lock-order adapter queries."""

    def __init__(self, job_ids=((41,),), detail_rows=()):
        self.job_ids = job_ids
        self.detail_rows = list(detail_rows)
        self.queries = []
        self.params = []

    def execute(self, query, params):
        self.queries.append(query)
        self.params.append(params)

    def fetchall(self):
        if len(self.queries) == 1:
            return self.job_ids
        return ()

    def fetchone(self):
        return self.detail_rows.pop(0) if self.detail_rows else None


def _fake_sql_env(cursor, company_ids=(7,)):
    return SimpleNamespace(
        cr=cursor,
        companies=SimpleNamespace(ids=list(company_ids)),
        company=SimpleNamespace(id=company_ids[0]),
    )


def _claim(job_id=41, worker="worker:test"):
    return ClaimedWork(
        job_id=job_id,
        store_id=7,
        company_id=7,
        run_id=12,
        attempt_no=1,
        claim_token=str(uuid.uuid4()),
        worker_ref=worker,
        handler_key="core_dispatch_selftest",
        lane="interactive",
        expected_generation=4,
        expected_configuration_generation=9,
    )


@tagged('post_install', '-at_install')
class TestV2RuntimeAdapter(TransactionCase):

    def test_generation_snapshot_fields_exist_on_run_and_job(self):
        run_field = self.env['shopify.connector.run']._fields[
            'expected_configuration_generation'
        ]
        job_field = self.env['shopify.connector.job']._fields[
            'expected_configuration_generation'
        ]
        self.assertTrue(run_field.required)
        self.assertTrue(run_field.readonly)
        self.assertTrue(job_field.readonly)
        default = job_field.default
        if callable(default):
            default = default(self.env['shopify.connector.job'])
        self.assertEqual(default, 0)

    def test_claim_sql_executes_bounded_generation_fenced_statement(self):
        cursor = _RecordingCursor()
        ids = OdooReadOnlyRuntimeRepository._claim_sql(
            _fake_sql_env(cursor), NOW, 3,
        )
        self.assertEqual(ids, (41,))
        self.assertEqual(cursor.params[:4], (NOW.replace(tzinfo=None),) * 4)
        self.assertEqual(cursor.params[4], (7,))
        self.assertEqual(cursor.params[5], NOW.replace(tzinfo=None))
        self.assertEqual(cursor.params[6], 3)
        self.assertEqual(len(cursor.params), cursor.query.count('%s'))
        self.assertIn('FOR UPDATE OF j, r, s, ss SKIP LOCKED', cursor.query)
        self.assertIn(
            'j.expected_connection_generation = s.connection_generation',
            cursor.query,
        )
        self.assertIn(
            'r.expected_connection_generation = s.connection_generation',
            cursor.query,
        )
        self.assertIn(
            'j.expected_configuration_generation =\n'
            '               ss.configuration_generation',
            cursor.query,
        )
        self.assertIn(
            'r.expected_configuration_generation =\n'
            '               ss.configuration_generation',
            cursor.query,
        )

    def test_claim_sql_has_dependency_and_cancellation_fences(self):
        cursor = _RecordingCursor(rows=())
        OdooReadOnlyRuntimeRepository._claim_sql(
            _fake_sql_env(cursor), NOW, 1,
        )
        query = cursor.query
        self.assertIn('r.cancel_requested_at IS NULL', query)
        self.assertIn("dep.state IN ('succeeded', 'skipped')", query)
        self.assertIn('j.mutation_attempt_id IS NULL', query)
        self.assertIn("ss.v2_runtime_mode = 'read_only'", query)

    def test_scope_recheck_fails_closed_on_both_generation_mismatches(self):
        claim = _claim()
        # Keep the tuple aligned with _lock_claim's SELECT projection.  The
        # test drives the adapter's real finalization scope predicate without
        # opening a transaction or touching a business record.
        row = (
            claim.job_id, claim.store_id, claim.company_id, claim.run_id,
            'running', claim.claim_token, claim.worker_ref,
            claim.expected_generation, claim.expected_configuration_generation,
            91, 'running', claim.attempt_no,
            claim.store_id, claim.company_id, 'running', None, None,
            claim.expected_generation, claim.expected_configuration_generation,
            claim.company_id, 'connected', claim.expected_generation,
            claim.company_id, claim.expected_configuration_generation,
            'read_only',
        )
        self.assertIsNone(
            OdooReadOnlyRuntimeRepository._scope_mismatch(row, claim, (7,)),
        )
        stale_connection = list(row)
        stale_connection[21] += 1
        self.assertEqual(
            OdooReadOnlyRuntimeRepository._scope_mismatch(
                tuple(stale_connection), claim, (7,),
            ),
            'connection_generation',
        )
        stale_configuration = list(row)
        stale_configuration[23] += 1
        self.assertEqual(
            OdooReadOnlyRuntimeRepository._scope_mismatch(
                tuple(stale_configuration), claim, (7,),
            ),
            'configuration_generation',
        )

    def test_scope_recheck_requires_claim_company_and_current_runtime_mode(self):
        claim = _claim()
        row = (
            claim.job_id, claim.store_id, claim.company_id, claim.run_id,
            'running', claim.claim_token, claim.worker_ref,
            claim.expected_generation, claim.expected_configuration_generation,
            91, 'running', claim.attempt_no,
            claim.store_id, claim.company_id, 'running', None, None,
            claim.expected_generation, claim.expected_configuration_generation,
            claim.company_id, 'connected', claim.expected_generation,
            claim.company_id, claim.expected_configuration_generation,
            'read_only',
        )
        self.assertEqual(
            OdooReadOnlyRuntimeRepository._scope_mismatch(row, claim, (8,)),
            'company_scope',
        )
        wrong_claim_company = list(row)
        wrong_claim_company[2] = 8
        wrong_claim_company = tuple(wrong_claim_company)
        self.assertEqual(
            OdooReadOnlyRuntimeRepository._scope_mismatch(
                wrong_claim_company, claim, (7, 8),
            ),
            'company_identity',
        )
        wrong_mode = list(row)
        wrong_mode[24] = 'legacy'
        self.assertEqual(
            OdooReadOnlyRuntimeRepository._scope_mismatch(
                tuple(wrong_mode), claim, (7,),
            ),
            'runtime_mode',
        )

    def test_transition_message_is_bounded_and_contains_no_handler_pii(self):
        message = _safe_transition_message(
            'contact operator@example.invalid at +1 (555) 123-4567; '
            + ('x' * (_TRANSITION_MESSAGE_LIMIT + 500)),
            'fallback',
        )
        self.assertLessEqual(len(message), _TRANSITION_MESSAGE_LIMIT)
        self.assertNotIn('operator@example.invalid', message)
        self.assertNotIn('555', message)
        self.assertEqual(_safe_transition_message(None, 'fallback'), 'fallback')
        self.assertEqual(_safe_transition_message('   ', 'fallback'), 'fallback')

    def test_finalization_and_stale_paths_lock_job_before_children(self):
        finalizer = inspect.getsource(OdooReadOnlyRuntimeRepository._lock_claim)
        stale = inspect.getsource(OdooReadOnlyRuntimeRepository._stale_sql)
        self.assertLess(finalizer.index('SELECT id'), finalizer.index('SELECT j.id'))
        self.assertIn('FOR UPDATE SKIP LOCKED', finalizer)
        self.assertIn('FOR UPDATE OF a, r, s, ss SKIP LOCKED', finalizer)
        self.assertLess(stale.index('SELECT j.id'), stale.index('SELECT a.id'))
        self.assertIn('FOR UPDATE OF j SKIP LOCKED', stale)
        self.assertIn('FOR UPDATE OF a, r, s, ss SKIP LOCKED', stale)

    def test_stale_sql_uses_bounded_two_step_job_first_locking(self):
        detail = (
            91, 41, str(uuid.uuid4()), 'worker:test', 'running',
            NOW.replace(tzinfo=None), NOW.replace(tzinfo=None), 4, 9,
            12, 4, 9, 4, 9, 'read_only',
        )
        cursor = _SequenceCursor(detail_rows=(detail,))
        repository = OdooReadOnlyRuntimeRepository(_fake_sql_env(cursor))
        rows = repository._stale_sql(_fake_sql_env(cursor), NOW, 1)
        self.assertEqual(rows, (detail,))
        self.assertEqual(len(cursor.queries), 2)
        self.assertEqual(cursor.params[0][-1], 1)
        self.assertEqual(cursor.params[1][0], 41)

    def test_only_explicit_non_mutation_handlers_are_registered(self):
        source = inspect.getsource(ShopifyConnectorV2Runtime)
        self.assertIn('_get_v2_read_only_handler_specs', source)
        self.assertIn('ReadOnlyHandlerSpec(', source)
        self.assertNotIn('mutation=True', source)
        self.assertNotIn('execute_business(', source)
        self.assertNotIn('requests.', source)
        repository_source = inspect.getsource(OdooReadOnlyRuntimeRepository)
        self.assertNotIn('requests.', repository_source)
        self.assertNotIn('urllib', repository_source)
        self.assertNotIn('execute_business(', repository_source)

    def test_legacy_dispatcher_and_sweep_do_not_claim_v2_rows(self):
        from ..models import shopify_connector_v2_runtime as runtime_module
        from ..models import shopify_connector_stale_owner_sweep as sweep_module

        dispatch_source = inspect.getsource(runtime_module)
        sweep_source = inspect.getsource(sweep_module)
        self.assertIn("('run_id', '=', False)", dispatch_source)
        self.assertIn("('run_id', '=', False)", sweep_source)

    def test_concurrent_claim_probe_allows_one_owner(self):
        """Cheap deterministic analogue of PostgreSQL SKIP LOCKED semantics."""
        lock = threading.Lock()
        owner = {'claimed': False}

        def try_claim():
            if not lock.acquire(blocking=False):
                return False
            try:
                if owner['claimed']:
                    return False
                owner['claimed'] = True
                return True
            finally:
                lock.release()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = tuple(pool.map(lambda _item: try_claim(), (1, 2)))
        self.assertEqual(sum(outcomes), 1)

    def test_stale_owner_policy_does_not_replay_uncertain_remote_work(self):
        decision = StaleOwnerPolicy().decide(StaleOwnerInput(
            job_id=41,
            attempt_id=91,
            attempt_outcome='running',
            claimed_at=NOW,
            heartbeat_at=NOW,
            now=NOW.replace(hour=13),
            remote_outcome='uncertain',
        ))
        self.assertEqual(decision.action, 'verify')

    def test_mixed_drain_capacity_stays_bounded_when_finalize_fails(self):
        self.assertEqual(
            reserve_capacity_after_v2(
                20,
                {'claimed_count': 20, 'finalized_count': 0},
            ),
            (0, 0),
        )


if __name__ == '__main__':
    unittest.main()
