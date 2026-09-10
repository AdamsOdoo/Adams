"""Exercise the adapter's SQL/ORM boundary with deferred job-state writes.

This cheap regression supplements the real P10 committed-cursor regressions;
it cannot establish PostgreSQL lock or Odoo flush behavior.
"""
import ast
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import unittest

from tools.tests.test_v2_runtime_decisions import project_run_state

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / 'addons/shopify_connector_core/models'
SOURCE = MODELS / 'shopify_connector_v2_runtime_common.py'


def projector():
    method = next(node for node in ast.walk(ast.parse(SOURCE.read_text()))
                  if isinstance(node, ast.FunctionDef)
                  and node.name == 'refresh_run_state')
    method.decorator_list = []
    namespace = {'project_run_state': project_run_state,
                 'fields': SimpleNamespace(Datetime=SimpleNamespace(now=lambda: 'now'))}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['refresh_run_state']


class TestRuntimeProjectionFlush(unittest.TestCase):
    def test_deferred_state_is_visible_before_aggregate_for_every_outcome(self):
        for state, target in (
            ('cancelled', 'cancelled'),
            ('blocked_manual_review', 'blocked_manual_review'),
            ('retry_waiting', 'waiting'),
            ('succeeded', 'succeeded'),
            ('failed_final', 'failed_terminal'),
        ):
            with self.subTest(state=state):
                durable = {1: 'running'}
                flushed = []
                run = SimpleNamespace(id=7, state='running', cancel_requested_at=state == 'cancelled')
                run.exists = lambda: True
                run._finish_service = lambda value, **kw: setattr(run, 'state', value)
                run._transition_service = lambda value: setattr(run, 'state', value)

                def flush(fields):
                    self.assertEqual(fields, ['state'])
                    flushed.append(1)
                    durable[1] = state

                def execute(query, params):
                    self.assertEqual(flushed, [1])
                    self.assertEqual(params, [7])

                cursor = SimpleNamespace(execute=execute, fetchall=lambda: list(Counter(durable.values()).items()))
                projector()(SimpleNamespace(cr=cursor), run,
                            changed_job=SimpleNamespace(flush_recordset=flush))
                self.assertEqual(run.state, target)

    def test_bounded_cancel_projection_retains_active_sibling(self):
        states = ['running', 'running']
        run = SimpleNamespace(id=7, state='running', cancel_requested_at=True)
        run.exists = lambda: True
        run._finish_service = lambda value, **kw: setattr(run, 'state', value)
        run._transition_service = lambda value: setattr(run, 'state', value)
        cursor = SimpleNamespace(execute=lambda *args: None,
                                 fetchall=lambda: list(Counter(states).items()))
        for index, expected in ((0, 'running'), (1, 'cancelled')):
            job = SimpleNamespace(flush_recordset=lambda fields: states.__setitem__(index, 'cancelled'))
            projector()(SimpleNamespace(cr=cursor), run, changed_job=job)
            self.assertEqual(run.state, expected)

    def test_every_projection_caller_identifies_its_locked_changed_job(self):
        callers = []
        for filename in ('shopify_connector_v2_runtime_repository.py',
                         'shopify_connector_v2_runtime_stale.py'):
            for node in ast.walk(ast.parse((MODELS / filename).read_text())):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == '_refresh_run_state'):
                    callers.append(node)
                    keyword = next(kw for kw in node.keywords if kw.arg == 'changed_job')
                    self.assertEqual(ast.unparse(keyword.value), 'job')
        self.assertEqual(len(callers), 6)
