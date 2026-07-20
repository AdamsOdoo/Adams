"""CORE-R2 foundation-slice tests (AR-047, gate `4952145926`; correction review
`4680664964`).

These tests exercise the *admission half* of the CORE-R2 disconnect-quiescence
mechanism delivered in this slice: the committed `shopify.connector.call.lease`
model, the `execute_business` context-manager (with its `execute()`-parity
response/error contract and deterministic exception precedence), the `_admit`
store-row-locked admission, `_release_lease`, the single-token `_send` contract,
and the enqueue-time connection-epoch capture. They do NOT test the disconnect
controller, `disconnecting` lifecycle, or `timed_out`/`completed` finalization —
those are deliberately later CORE-R2 slices.

Two test styles are used, on purpose:

* `TransactionCase` classes drive the **real production** `execute_business`/
  `_admit`/`_send`/`_release_lease` path. Under Odoo test mode the side cursor
  that `_admit` opens (`registry.cursor()`) is a `TestCursor` sharing the single
  test connection, so these prove the admission *logic* (gate, ordering,
  token-once, API-parity, precedence, release) but cannot prove genuine
  cross-connection independence.
* `TestGenuineRealAdmission` (correction review `4680664964`, blocker 2) invokes
  the **real** `execute_business`/`_admit`/lease-ORM/credential/`_release_lease`
  path from genuine independent connections (`odoo.sql_db.db_connect`, never
  `registry.cursor()` for the worker/observer cursors). To let the production
  `_admit`'s own `registry.cursor()` side transaction commit to the real database
  — so an independent observer connection can see it — those tests patch the
  registry cursor factory to hand out real pooled cursors for the bounded test
  window. Raw SQL is used only for bounded observation and cleanup, never to
  create the lease under test. Fixtures are committed and torn down with durable,
  fail-loud, bounded cleanup and a fresh zero-residue verification.

No live Shopify call is made; the only transport seam replaced is `_send` (plus,
for the two exception-precedence tests, an injected `_release_lease` fault). No
lifecycle/state monkeypatch and no test-only timing hook is used.
"""

import ast
import contextlib
import importlib
import inspect
import logging
import queue
import re
import textwrap
import threading
import traceback
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import psycopg2
import psycopg2.errorcodes

import odoo.service.model as service_model
from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError, ValidationError
from odoo.service.model import retrying
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import shopify_connector_api_client as client_module
from ..models import shopify_connector_store as store_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    REASON_TOKEN_INVALID,
    ShopifyClientError,
    ShopifyQuiescedError,
)
from ..models.shopify_connector_job_dispatch import (
    DISCONNECT_QUIESCE_TIMEOUT,
    POLL_DELAY,
    RETRY_MAX_ATTEMPTS,
)
from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'

# The "business" fields the lease table is allowed to carry (everything else is
# an ORM magic column). Deliberately no token/credential/query/payload column.
EXPECTED_LEASE_FIELDS = {
    'store_id', 'lease_key', 'job_id', 'worker_ref', 'admitted_at', 'expires_at',
}
FORBIDDEN_LEASE_SUBSTRINGS = (
    'token', 'credential', 'secret', 'query', 'variable', 'payload', 'body',
    'customer', 'product', 'password',
)
# ORM magic/log-access columns, excluded when checking the declared business
# shape (explicit set, not `field.automatic`, so the assertion is deterministic
# across Odoo point releases).
MAGIC_FIELDS = {
    'id', 'display_name', 'create_uid', 'create_date', 'write_uid',
    'write_date', '__last_update',
}


def _duplicate_test_methods(source, relative):
    """Return duplicate direct method definitions from every test class."""
    tree = ast.parse(source, filename=relative)
    violations = []
    for class_node in ast.walk(tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        methods = [
            node for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        is_test_class = (
            class_node.name.startswith('Test')
            or any(method.name.startswith('test_') for method in methods)
        )
        if not is_test_class:
            continue
        first_lines = {}
        for method in methods:
            if method.name in first_lines:
                violations.append((
                    relative,
                    class_node.name,
                    method.name,
                    first_lines[method.name],
                    method.lineno,
                ))
            else:
                first_lines[method.name] = method.lineno
    return violations


def _ok_send(captured):
    """A fake `_send` that records what it was handed and returns a real
    `FakeResponse` (200 OK) so `execute_business`'s `_normalize_response` runs
    exactly as it does for `execute()`.

    Replaces ONLY `_send`, makes no network call, and never reads credentials.
    """

    def fake_send(self, store, body, token=None):
        captured.setdefault('calls', []).append(1)
        captured['token'] = token
        captured['body'] = body
        return FakeResponse(200, json_body={'data': {'ok': True}})

    return fake_send


# ---------------------------------------------------------------------------
# Reusable AST source-guard helpers (CORE-R2 control-room review 4692156428,
# test-only correction). Shared by the source guards in this file AND
# `test_credential_service.py` (imported there). Every helper inspects a
# method's EXECUTABLE ast -- never the raw source text -- and excludes the
# method's own docstring, so a docstring/comment that mentions a forbidden
# token (`sudo()`, `SKIP LOCKED`, `action_clear_token`, `call.lease`) is NOT a
# false positive. This is the same `ast.parse` discipline the pre-existing
# sibling guard `test_admit_lifecycle_commits_and_closes_before_transport`
# already used; these helpers generalise it so all four naive
# `assertNotIn(<token>, inspect.getsource(...))` guards become docstring-robust
# without weakening a single safety assertion. `test_source_guard_detector_*`
# (this file) proves each helper both FIRES on real unsafe executable code and
# IGNORES a docstring-only mention.
# ---------------------------------------------------------------------------
def guard_fn_ast(func):
    """Return the `ast.FunctionDef` for a (bound or unbound) method's source."""
    return ast.parse(textwrap.dedent(inspect.getsource(func))).body[0]


def _guard_executable_body(fn):
    """The executable body statements of a FunctionDef, excluding a leading
    string-literal docstring (comments are already absent from the AST)."""
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


def _guard_executable_nodes(fn):
    """Every AST node reachable from the executable body (docstring excluded),
    so a docstring's own sub-nodes are never inspected."""
    nodes = []
    for stmt in _guard_executable_body(fn):
        nodes.extend(ast.walk(stmt))
    return nodes


def guard_called_names(fn):
    """Set of call target identifiers in the executable body
    (`x.sudo()` -> `sudo`, `foo()` -> `foo`)."""
    names = set()
    for node in _guard_executable_nodes(fn):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                names.add(target.attr)
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return names


def guard_execute_sql(fn):
    """Concatenated string literals passed as the first argument to any
    `.execute(...)` call in the executable body -- the SQL a cursor runs."""
    parts = []
    for node in _guard_executable_nodes(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'execute' and node.args):
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                parts.append(arg.value)
    return ' '.join(parts)


def guard_str_constants(fn):
    """All string-literal constants in the executable body (docstring
    excluded) -- e.g. a model xmlid used in a `self.env['...']` lookup."""
    return [
        node.value for node in _guard_executable_nodes(fn)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def guard_identifiers(fn):
    """All Name ids, attribute names, and keyword-argument names in the
    executable body -- used to forbid an identifier such as `lease_key`."""
    out = set()
    for node in _guard_executable_nodes(fn):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.keyword) and node.arg:
            out.add(node.arg)
    return out


def guard_has_call_with_const_kwarg(fn, method_name, kwarg, value):
    """True if the executable body calls `<recv>.<method_name>(..., <kwarg>=<value>)`
    with a literal `value` (e.g. `try_lock_for_update(limit=1)`)."""
    for node in _guard_executable_nodes(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == method_name):
            for kw in node.keywords:
                if (kw.arg == kwarg and isinstance(kw.value, ast.Constant)
                        and kw.value.value == value):
                    return True
    return False


def guard_min_call_lineno(fn, attr, receiver_name=None):
    """Smallest source line of an executable `<recv>.<attr>(...)` call
    (optionally restricted to receiver `<receiver_name>`), or None."""
    linenos = []
    for node in _guard_executable_nodes(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == attr):
            if receiver_name is not None and not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == receiver_name):
                continue
            linenos.append(node.lineno)
    return min(linenos) if linenos else None


class TestCallLeaseModelSchema(TransactionCase):

    def test_connector_tests_have_no_duplicate_class_methods(self):
        addon_root = Path(__file__).resolve().parents[2]
        violations = []
        for path in sorted(addon_root.glob(
            'shopify_connector_*/tests/**/*.py'
        )):
            relative = str(path.relative_to(addon_root))
            violations.extend(_duplicate_test_methods(
                path.read_text(encoding='utf-8'), relative,
            ))
        self.assertFalse(violations, violations)

    def test_duplicate_class_method_detector_is_adversarially_proven(self):
        source = (
            'class TestAdversarial:\n'
            '    def test_same_name(self):\n'
            '        return 1\n'
            '    def test_same_name(self):\n'
            '        return 2\n'
        )
        self.assertEqual(
            _duplicate_test_methods(source, 'synthetic_duplicate.py'),
            [(
                'synthetic_duplicate.py', 'TestAdversarial',
                'test_same_name', 2, 4,
            )],
        )
    """The lease table shape + the client source-level guards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lease = cls.env['shopify.connector.call.lease']

    # 1. Lease model has no token/credential/query/payload field.
    def test_lease_has_no_secret_or_payload_field(self):
        field_names = set(self.Lease._fields)
        for fname in field_names:
            for bad in FORBIDDEN_LEASE_SUBSTRINGS:
                self.assertNotIn(
                    bad, fname.lower(),
                    'lease field %r must not reference %r' % (fname, bad),
                )
        # The declared (non-magic) columns are exactly the coordination minimum.
        business = set(self.Lease._fields) - MAGIC_FIELDS
        self.assertEqual(business, EXPECTED_LEASE_FIELDS)

    # 2. job_id is Integer, not Many2one; store_id is the only Many2one.
    def test_job_id_is_integer_not_m2o(self):
        self.assertEqual(self.Lease._fields['job_id'].type, 'integer')
        self.assertEqual(self.Lease._fields['store_id'].type, 'many2one')
        self.assertEqual(self.Lease._fields['store_id'].comodel_name,
                         'shopify.connector.store')

    # 3a. Lease key is unique (opacity is proven at admission, below).
    @mute_logger('odoo.sql_db')
    def test_lease_key_is_unique(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Lease Uniq Store',
            'shop_domain': 'lease-uniq-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        now = fields.Datetime.now()
        vals = {
            'store_id': store.id, 'lease_key': 'dup-key', 'job_id': 1,
            'admitted_at': now, 'expires_at': now,
        }
        self.Lease.create(vals)
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Lease.create(dict(vals))

    # 21. No advisory lock anywhere in the client; FOR SHARE is the primitive.
    def test_no_advisory_lock_in_client_source(self):
        source = inspect.getsource(client_module)
        self.assertNotIn('advisory', source.lower())
        self.assertNotIn('pg_advisory', source.lower())
        self.assertIn('FOR SHARE', source)

    # 22. No request/main cursor commit: every .commit()/.rollback() is on the
    # owned side cursor, never on self.env.cr / self._cr.
    def test_no_main_cursor_commit_in_client_source(self):
        source = inspect.getsource(client_module)
        self.assertNotIn('self.env.cr.commit', source)
        self.assertNotIn('self._cr.commit', source)
        self.assertNotIn('self.env.cr.rollback', source)
        committed = re.findall(r'(\w+)\.commit\(\)', source)
        self.assertTrue(committed, 'expected side-cursor commits to exist')
        self.assertTrue(
            all(name == 'side_cr' for name in committed),
            'only the owned side cursor may commit; found: %s' % committed,
        )

    # 20b. execute_business is the sole guarded public mutation boundary.
    def test_public_surface_adds_only_execute_business(self):
        ClientClass = client_module.ShopifyConnectorApiClient
        public = {
            name for name, value in vars(
                ClientClass
            ).items()
            if callable(value) and not name.startswith('_')
        }
        self.assertEqual(public, {'execute', 'execute_business'})
        self.assertIn(
            '_validate_graphql_operation',
            guard_called_names(guard_fn_ast(ClientClass.execute)),
        )
        self.assertIn(
            '_validate_graphql_operation',
            guard_called_names(guard_fn_ast(ClientClass._send_lifecycle)),
        )
        business_calls = guard_called_names(
            guard_fn_ast(ClientClass.execute_business)
        )
        self.assertIn('_validate_graphql_operation', business_calls)
        self.assertIn('_admit_mutation', business_calls)
        self.assertNotIn('_admit_mutation', guard_called_names(
            guard_fn_ast(ClientClass.execute)
        ))
        self.assertNotIn('_admit_mutation', guard_called_names(
            guard_fn_ast(ClientClass._send_lifecycle)
        ))

    # API-parity source guards (review 4680664964, blocker 1): execute_business
    # normalizes like execute(), keeps the two-arg legacy seam, uses the explicit
    # captured token, and carries the RRequestException->temporary taxonomy.
    def test_execute_business_source_normalizes_and_preserves_seam(self):
        source = inspect.getsource(client_module)
        self.assertIn('_normalize_response(store, response)', source)
        self.assertIn('self._send(store, body)', source)          # legacy 2-arg
        self.assertIn('self._send(store, body, token)', source)   # business 3-arg
        self.assertIn('REASON_TEMPORARY', source)


class TestBusinessAdmission(TransactionCase):
    """The real `execute_business`/`_admit`/`_release_lease` admission path,
    including the `execute()`-parity contract and exception precedence."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Client = cls.env['shopify.connector.api.client']
        cls.Lease = cls.env['shopify.connector.call.lease']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Admission Store',
            'shop_domain': 'admission-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN
        )
        # action_set_token() demotes a `connected` store to `reconnect_needed`
        # (a credential change invalidates the connected state); re-assert
        # `connected` so business enqueue + admission gates pass, mirroring the
        # canonical pattern in the existing dispatch/retry tests.
        cls.store.write({'state': 'connected'})
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # CORE-R2 admission runs its gate/lease insert on a side transaction it
        # opens itself via `self.env.registry.cursor()` (durable, independent —
        # the invariant proven cross-connection by TestGenuineRealAdmission). A
        # plain TransactionCase does NOT patch the registry, so that call returns
        # a genuinely independent connection which cannot see this class's
        # *uncommitted* fixture store/job — `_admit`'s `SELECT ... FOR SHARE`
        # then finds `row is None` and fails closed with ShopifyQuiescedError.
        # `enter_registry_test_mode` (Odoo's sanctioned mechanism) makes every
        # `registry.cursor()` reuse the single test connection as a TestCursor,
        # so the fixture and the committed lease are visible cross-cursor — the
        # exact "TestCursor sharing the single test connection" this module's
        # docstring relies on to prove the admission *logic*. It changes no
        # production behaviour (real stores are committed) and is auto-left on
        # teardown; genuine cross-connection independence stays proven by
        # TestGenuineRealAdmission.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _make_job(self, store=None):
        store = store or self.store
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash=uuid.uuid4().hex,
        )

    def _lease_count(self, store=None):
        store = store or self.store
        return self.Lease.search_count([('store_id', '=', store.id)])

    # --- Gate refusals (fail closed; no lease, no _send) ---------------

    # 4. Missing job is refused.
    def test_missing_job_refused(self):
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(False, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 5. Wrong-store job is refused.
    def test_wrong_store_job_refused(self):
        other = self.env['shopify.connector.store'].create({
            'name': 'Other Store',
            'shop_domain': 'other-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        job_other = self._make_job(store=other)
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job_other, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 6. Disconnected store is refused.
    def test_disconnected_store_refused(self):
        job = self._make_job()
        self.store.write({'state': 'disconnected'})
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 7. Generation mismatch is refused.
    def test_generation_mismatch_refused(self):
        job = self._make_job()  # captures the store's current epoch at enqueue
        # Bump the store epoch PAST the job's captured value to force a mismatch,
        # regardless of the fixture's base epoch (CORE-R2 review 4690639375 #3:
        # a connected `action_set_token` now bumps the epoch, so the setUpClass
        # fixture is no longer necessarily at 0 -- derive the mismatch from the
        # job's own captured generation rather than a hard-coded 0->1).
        self.store.write({
            'connection_generation': job.expected_connection_generation + 1,
        })
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # --- execute()-parity contract (review 4680664964, blocker 1) ------

    # C1. Missing shop_domain/api_version -> same UserError as execute();
    # no lease, no _send (checked before admission).
    def test_missing_store_config_raises_user_error_before_admission(self):
        job = self._make_job()
        self.env.flush_all()

        class _StubStore:
            def __init__(self, shop_domain, api_version, sid):
                self.shop_domain = shop_domain
                self.api_version = api_version
                self.id = sid

        sent = []

        def spy_send(self, store, body, token=None):
            sent.append(1)
            return FakeResponse(200, json_body={'data': {}})

        with patch.object(type(self.Client), '_send', spy_send):
            for stub in (
                _StubStore(False, '2026-07', self.store.id),
                _StubStore('x.myshopify.com', False, self.store.id),
            ):
                with self.assertRaises(UserError):
                    with self.Client.execute_business(job, stub, 'q'):
                        pass
        self.assertEqual(sent, [])
        self.assertEqual(self._lease_count(), 0)

    # C2. Missing credential -> accepted ShopifyClientError taxonomy, before any
    # lease or _send, with exactly one credential read.
    def test_missing_credential_raises_shopify_client_error(self):
        nocred = self.env['shopify.connector.store'].create({
            'name': 'No Credential Store',
            'shop_domain': 'nocred-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        job = self._make_job(store=nocred)
        Cred = type(self.env['shopify.connector.store.credential'])
        reads = []
        sent = []

        def counting_empty(self, store):
            reads.append(1)
            return False

        def spy_send(self, store, body, token=None):
            sent.append(1)
            return FakeResponse(200, json_body={'data': {}})

        self.env.flush_all()
        with patch.object(Cred, '_get_access_token', counting_empty):
            with patch.object(type(self.Client), '_send', spy_send):
                with self.assertRaises(ShopifyClientError) as caught:
                    with self.Client.execute_business(job, nocred, 'q'):
                        pass
        exc = caught.exception
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)
        self.assertEqual(exc.reason, REASON_TOKEN_INVALID)
        self.assertEqual(sent, [])          # no _send
        self.assertEqual(reads, [1])        # exactly one credential read
        self.assertEqual(self._lease_count(nocred), 0)   # no lease

    # C3. Success yields the SAME normalized dict shape as execute(); lease held
    # through normalization and the caller body, released after.
    def test_success_yields_normalized_dict_like_execute(self):
        job = self._make_job()
        success = _success_body(domain=self.store.shop_domain)

        def ok_send(self, store, body, token=None):
            return FakeResponse(200, json_body=success)

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', ok_send):
            with self.Client.execute_business(job, self.store, 'q') as result:
                self.assertIn('data', result)
                self.assertIn('throttle_status', result)
                self.assertEqual(
                    result['data']['shop']['myshopifyDomain'],
                    self.store.shop_domain,
                )
                self.assertEqual(self._lease_count(), 1)   # held through body
        self.assertEqual(self._lease_count(), 0)           # released after

    # C4/#6. requests.RequestException -> ERROR_TEMPORARY; lease released (even
    # on a pre-yield failure); no token/header/body in the raised error.
    def test_request_exception_mapped_to_temporary_and_releases(self):
        job = self._make_job()

        def raising_send(self, store, body, token=None):
            raise client_module.requests.exceptions.ConnectTimeout(
                'net down token=%s' % DUMMY_TOKEN
            )

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', raising_send):
            with self.assertRaises(ShopifyClientError) as caught:
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        exc = caught.exception
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)
        self.assertNotIn(DUMMY_TOKEN, str(exc))
        self.assertNotIn(DUMMY_TOKEN, exc.technical_detail or '')
        self.assertEqual(self._lease_count(), 0)           # released

    # C5. GraphQL/auth error passes through _normalize_response; accepted
    # ShopifyClientError taxonomy is preserved; lease released.
    def test_graphql_error_normalized_taxonomy_preserved_and_releases(self):
        job = self._make_job()

        def denied_send(self, store, body, token=None):
            return FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            })

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', denied_send):
            with self.assertRaises(ShopifyClientError) as caught:
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        self.assertEqual(caught.exception.error_class, ERROR_AUTH)
        self.assertTrue(caught.exception.credential_invalid)
        self.assertEqual(self._lease_count(), 0)

    # --- token-once / ordering / release -------------------------------

    # 8/16. Token read exactly once (at admission) and handed to _send.
    def test_token_read_once_and_passed_to_send(self):
        job = self._make_job()
        Cred = type(self.env['shopify.connector.store.credential'])
        reads = []
        captured = {}

        def counting_get(self, store):
            reads.append(1)
            return 'TOKEN_SNAPSHOT_XYZ'

        self.env.flush_all()
        with patch.object(Cred, '_get_access_token', counting_get):
            with patch.object(type(self.Client), '_send', _ok_send(captured)):
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        self.assertEqual(reads, [1])                        # exactly once
        self.assertEqual(captured['token'], 'TOKEN_SNAPSHOT_XYZ')

    # 17. _send does not reread credentials when given a token; reads when not.
    def test_send_reads_credential_only_when_token_absent(self):
        Client = self.Client
        Cred = type(self.env['shopify.connector.store.credential'])
        posted = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            posted['headers'] = headers
            return FakeResponse(200, json_body={'data': {}})

        reads = []

        def counting_get(self, store):
            reads.append(1)
            return 'TOKEN_FROM_CRED'

        with patch.object(client_module.requests, 'post', fake_post):
            with patch.object(Cred, '_get_access_token', counting_get):
                Client._send(self.store, {'query': 'q'}, token='SNAP')
                self.assertEqual(reads, [])                 # no reread
                self.assertEqual(
                    posted['headers']['X-Shopify-Access-Token'], 'SNAP'
                )
                Client._send(self.store, {'query': 'q'})
                self.assertEqual(reads, [1])                # legacy path reads
                self.assertEqual(
                    posted['headers']['X-Shopify-Access-Token'],
                    'TOKEN_FROM_CRED',
                )

    # 3b/9/10. Opaque key; lease committed before _send begins; visible in body.
    def test_lease_opaque_committed_before_send_and_visible_in_context(self):
        job = self._make_job()
        seen = {}

        def fake_send(self_, store, body, token=None):
            seen['count_at_send'] = self.Lease.search_count(
                [('store_id', '=', store.id)]
            )
            return FakeResponse(200, json_body={'data': {}})

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', fake_send):
            with self.Client.execute_business(job, self.store, 'q') as result:
                seen['count_in_body'] = self._lease_count()
                lease = self.Lease.search([('store_id', '=', self.store.id)])
                seen['key'] = lease.lease_key
                self.assertEqual(result['data'], {})
        self.assertEqual(seen['count_at_send'], 1)   # 9: committed before send
        self.assertEqual(seen['count_in_body'], 1)   # 10: visible in context
        # 3b: opaque key. It is a genuine random uuid4 (version nibble == 4,
        # RFC-4122 variant), so it encodes no store id, job id, or token and
        # carries no recoverable business identity. NOTE: a decimal id such as
        # `str(store.id)` (e.g. '15') can appear inside a random 32-char hex key
        # purely by chance, so a substring assertion on the id is mathematically
        # unsound and intermittently fails — the uuid4-version/variant check is
        # the correct, deterministic opacity proof. The token is long and random,
        # so its non-containment remains a valid (security-critical) guard.
        self.assertRegex(seen['key'], r'^[0-9a-f]{32}$')
        parsed_key = uuid.UUID(seen['key'])
        self.assertEqual(parsed_key.version, 4)
        self.assertEqual(parsed_key.variant, uuid.RFC_4122)
        self.assertNotIn(DUMMY_TOKEN, seen['key'])

    # 11. Normal exit releases the lease.
    def test_normal_exit_releases_lease(self):
        job = self._make_job()
        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with self.Client.execute_business(job, self.store, 'q'):
                self.assertEqual(self._lease_count(), 1)
        self.assertEqual(self._lease_count(), 0)

    # 7/12. Caller-body exception releases the lease and re-raises unchanged.
    def test_exception_exit_releases_and_reraises(self):
        job = self._make_job()

        class Boom(Exception):
            pass

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with self.assertRaises(Boom):
                with self.Client.execute_business(job, self.store, 'q'):
                    self.assertEqual(self._lease_count(), 1)
                    raise Boom()
        self.assertEqual(self._lease_count(), 0)

    # --- deterministic exception precedence (review 4680664964, blocker 3) ---

    # C8. Successful body + release failure -> the release error propagates.
    def test_release_failure_after_successful_body_propagates(self):
        job = self._make_job()

        class ReleaseBoom(Exception):
            pass

        def failing_release(self, lease_key):
            raise ReleaseBoom('release failed')

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              failing_release):
                with self.assertRaises(ReleaseBoom):
                    with self.Client.execute_business(job, self.store,
                                                      'q') as result:
                        self.assertEqual(result['data'], {'ok': True})

    # C9. Body error + release error -> body error stays primary; release error
    # is chained as its cause (classification not replaced).
    def test_body_error_with_release_failure_preserves_primary(self):
        job = self._make_job()

        class BodyBoom(Exception):
            pass

        class ReleaseBoom(Exception):
            pass

        def failing_release(self, lease_key):
            raise ReleaseBoom('release failed')

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              failing_release):
                with self.assertRaises(BodyBoom) as caught:
                    with self.Client.execute_business(job, self.store, 'q'):
                        raise BodyBoom('body failed')
        self.assertIsInstance(caught.exception.__cause__, ReleaseBoom)

    # C10. Successful release uses a BARE re-raise: the SAME caller exception
    # object propagates with its ORIGINAL traceback (incl. the body raise site),
    # release runs exactly once, and there is no chained cause (review
    # `4681564744`).
    def test_body_exception_bare_reraise_preserves_traceback_and_releases_once(
            self):
        job = self._make_job()

        class Boom(Exception):
            pass

        raised = Boom('body failed')
        releases = []
        real_release = type(self.Client)._release_lease

        def counting_release(client_self, lease_key):
            releases.append(1)
            return real_release(client_self, lease_key)

        self.env.flush_all()
        captured_exc = None
        captured_tb_text = ''
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              counting_release):
                try:
                    with self.Client.execute_business(job, self.store, 'q'):
                        raise raised
                except Boom as exc:
                    # Capture the LIVE exception + traceback in the real handler.
                    # unittest's assertRaises stores the exception via
                    # `with_traceback(None)`, which would strip __traceback__ and
                    # make the "body raise site kept" assertion vacuous (it always
                    # sees ''). Capturing here proves the bare re-raise preserved
                    # the SAME object AND its ORIGINAL traceback (incl. the body
                    # raise site) — a stronger check than the assertRaises form.
                    captured_exc = exc
                    captured_tb_text = ''.join(
                        traceback.format_tb(exc.__traceback__))
        self.assertIsNotNone(captured_exc, 'Boom did not propagate')
        self.assertIs(captured_exc, raised)               # same object/identity
        self.assertIsNone(captured_exc.__cause__)         # release ok -> no chain
        self.assertEqual(releases, [1])                   # released exactly once
        self.assertIn(                                    # body raise site kept
            'test_body_exception_bare_reraise', captured_tb_text)
        self.assertEqual(self._lease_count(), 0)          # lease released

    # 18. Token never appears in any lease field.
    def test_token_never_appears_in_lease_rows(self):
        job = self._make_job()
        captured = {}
        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send(captured)):
            with self.Client.execute_business(job, self.store, 'q'):
                leases = self.Lease.search([('store_id', '=', self.store.id)])
                self.assertEqual(len(leases), 1)
                for lease in leases:
                    for fname, field in lease._fields.items():
                        if field.type in ('char', 'text'):
                            value = lease[fname]
                            if value:
                                self.assertNotIn(DUMMY_TOKEN, value)


@tagged('post_install', '-at_install')
class TestGenuineRealAdmission(TransactionCase):
    """Genuine independent-connection tests of the REAL execute_business/_admit
    path (correction review `4680664964`, blocker 2).

    Each worker owns a `db_connect` main cursor + Environment created AFTER the
    fixtures commit (so, under Odoo's REPEATABLE READ snapshot, it sees them).
    `execute_business`/`_admit`/the lease ORM/`_get_access_token`/`_release_lease`
    are the REAL production code. The production `_admit` opens its own
    `registry.cursor()` side transaction — the mechanism under test — which is
    made genuinely independent (real pooled cursor, real commit, observable
    cross-connection) by patching the registry cursor factory for the bounded
    test window. Raw SQL is used only to OBSERVE committed leases and to clean up;
    it never creates the lease under test. The full two-server production-path
    proof (packet T-19) remains a deferred Odoo.sh runtime item (SRR-09 / RR-4).
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    # --- genuine-connection helpers ------------------------------------

    def _open_bounded(self, dbname):
        """Open a genuine pooled cursor and apply BOTH transaction-local
        PostgreSQL limits (statement_timeout + lock_timeout) via parameterized
        `set_config(..., true)`. If the bound setup fails, close the cursor and
        re-raise; return only after a successful setup — so no genuine worker or
        production side cursor is ever left unbounded (review `4681564744`)."""
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _real_registry_cursor(self, dbname):
        """A registry.cursor() replacement handing out **bounded** real pooled
        cursors, so every production `_admit`/`_release_lease` side transaction is
        time-bounded. Accepts/ignores any registry.cursor() args (e.g.
        readonly=)."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _sanitize(self, exc, phase):
        """A type-only, non-sensitive finding for a worker-thread failure.

        Records ONLY the fixed `phase`, the exception TYPE NAME, and (when it is a
        connector error) the safe fixed `error_class` enum — never `str`/`repr` of
        the exception, SQL, paths, credentials, payloads, or tokens.
        """
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _safe_worker_teardown(self, wcr, diagnostics):
        """Roll back + close a worker cursor, surfacing (never swallowing) each
        failure as a SEPARATE sanitized finding so one cannot hide the other."""
        if wcr is None:
            return
        try:
            wcr.rollback()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'rollback'))
        try:
            wcr.close()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'cursor_close'))

    def _drain(self, diagnostics):
        """Collect all sanitized findings from the thread-safe queue."""
        findings = []
        while True:
            try:
                findings.append(diagnostics.get_nowait())
            except queue.Empty:
                break
        return findings

    def _assert_workers_dead(self, threads):
        """Fail loudly (fixed, non-sensitive message) if any worker is alive."""
        alive = sum(1 for t in threads if t is not None and t.is_alive())
        self.assertEqual(
            alive, 0, 'worker thread still alive at the cleanup boundary')

    def _commit_fixtures(self, dbname, n_jobs):
        """On an independent (bounded) connection, create+commit a connected
        store, its credential, and `n_jobs` matching business jobs."""
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Real Admission Store',
                'shop_domain': 'genuine-real-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN
            )
            # action_set_token() demotes `connected` -> `reconnect_needed`;
            # re-assert `connected` before enqueue/admission (see setUpClass).
            store.write({'state': 'connected'})
            job_ids = []
            for _ in range(n_jobs):
                job = env['shopify.connector.job.enqueue'].enqueue(
                    store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash=uuid.uuid4().hex,
                )
                job_ids.append(job.id)
            store_id = store.id
            setup.commit()
            return store_id, job_ids
        finally:
            setup.close()

    def _committed_lease_rows(self, dbname, store_id):
        """Observe committed leases from a fresh, bounded independent connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT lease_key, job_id FROM shopify_connector_call_lease "
                "WHERE store_id = %s ORDER BY lease_key", (store_id,))
            rows = obs.fetchall()
            obs.rollback()
            return rows
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id, job_ids):
        """Durable, bounded, fail-loud teardown + fresh zero-residue check.

        Deletes job logs BEFORE jobs (FK `ondelete='restrict'`), then leases,
        jobs, credential, store. DELETEs are not swallowed → fail-loud."""
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            if job_ids:
                cr.execute(
                    "DELETE FROM shopify_connector_job_log "
                    "WHERE job_id = ANY(%s)", (list(job_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            if job_ids:
                cr.execute(
                    "DELETE FROM shopify_connector_job WHERE id = ANY(%s)",
                    (list(job_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        self._assert_zero_residue(dbname, store_id, job_ids)

    def _assert_zero_residue(self, dbname, store_id, job_ids):
        """Fresh, bounded verifier: zero leases, stores, credentials, jobs, AND
        job logs for the synthetic job ids. Uses unittest assertions with fixed,
        non-sensitive messages; always closes the verifier cursor."""
        v = self._open_bounded(dbname)
        try:
            v.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(v.fetchone()[0], 0, 'lease residue after cleanup')
            v.execute(
                "SELECT count(*) FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            self.assertEqual(v.fetchone()[0], 0, 'store residue after cleanup')
            v.execute(
                "SELECT count(*) FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(
                v.fetchone()[0], 0, 'credential residue after cleanup')
            if job_ids:
                v.execute(
                    "SELECT count(*) FROM shopify_connector_job "
                    "WHERE id = ANY(%s)", (list(job_ids),))
                self.assertEqual(v.fetchone()[0], 0, 'job residue after cleanup')
                v.execute(
                    "SELECT count(*) FROM shopify_connector_job_log "
                    "WHERE job_id = ANY(%s)", (list(job_ids),))
                self.assertEqual(
                    v.fetchone()[0], 0, 'job-log residue after cleanup')
            v.rollback()
        finally:
            v.close()

    # B. Real single admission: lease committed before _send, visible in the
    # context, and released on exit — all observed cross-connection.
    def test_real_admission_visible_before_send_and_released(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        worker_cr = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=1)
            worker_cr = self._open_bounded(dbname)
            worker_env = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = worker_env['shopify.connector.store'].browse(store_id)
            job = worker_env['shopify.connector.job'].browse(job_ids[0])
            Client = worker_env['shopify.connector.api.client']
            observed = {}

            # `client_self` is the api-client recordset bound by `self._send(...)`;
            # the test instance's `self` (for the observer helper) is captured by
            # closure.
            def observing_send(client_self, store_arg, body, token=None):
                observed['token'] = token
                observed['during_send'] = self._committed_lease_rows(
                    dbname, store_id)
                return FakeResponse(200, json_body={'data': {'ok': True}})

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', observing_send):
                    with Client.execute_business(
                            job, store, 'query { shop { id } }') as result:
                        observed['in_body'] = self._committed_lease_rows(
                            dbname, store_id)
                        observed['result'] = result
            observed['after'] = self._committed_lease_rows(dbname, store_id)

            self.assertEqual(len(observed['during_send']), 1)   # committed pre-send
            key, jid = observed['during_send'][0]
            self.assertEqual(jid, job_ids[0])
            self.assertRegex(key, r'^[0-9a-f]{32}$')            # opaque
            self.assertEqual(observed['token'], DUMMY_TOKEN)    # real snapshot
            self.assertEqual(len(observed['in_body']), 1)       # visible in ctx
            self.assertEqual(observed['result']['data'], {'ok': True})  # normalized
            self.assertEqual(len(observed['after']), 0)         # released on exit
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_ids)

    # C. Real caller-rollback independence: the committed lease survives the
    # worker's own main-transaction rollback, then releases on context exit.
    def test_real_admission_survives_caller_rollback(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        worker_cr = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=1)
            worker_cr = self._open_bounded(dbname)
            worker_env = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = worker_env['shopify.connector.store'].browse(store_id)
            job = worker_env['shopify.connector.job'].browse(job_ids[0])
            Client = worker_env['shopify.connector.api.client']
            observed = {}

            def ok_send(client_self, store_arg, body, token=None):
                return FakeResponse(200, json_body={'data': {'ok': True}})

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', ok_send):
                    with Client.execute_business(
                            job, store, 'query { shop { id } }'):
                        # the caller's OWN main transaction rolls back mid-context
                        worker_cr.rollback()
                        observed['after_rollback'] = self._committed_lease_rows(
                            dbname, store_id)
            observed['after_exit'] = self._committed_lease_rows(dbname, store_id)

            self.assertEqual(len(observed['after_rollback']), 1)  # independent
            self.assertEqual(observed['after_rollback'][0][1], job_ids[0])
            self.assertEqual(len(observed['after_exit']), 0)      # released
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_ids)

    # D. Two REAL concurrent admissions on one store: both enter without
    # blocking, both leases coexist with distinct keys and correct job ids, both
    # release.
    def test_two_real_concurrent_admissions_commit_distinct_leases(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        release_gate = threading.Event()
        diagnostics = queue.Queue()      # thread-safe, sanitized worker findings
        t1 = t2 = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=2)
            both_admitted = threading.Semaphore(0)

            def blocking_send(client_self, store_arg, body, token=None):
                # this worker's _admit has already committed its lease
                both_admitted.release()
                if not release_gate.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('release_gate not set within bound')
                return FakeResponse(200, json_body={'data': {'ok': True}})

            def worker(job_id):
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    store = wenv['shopify.connector.store'].browse(store_id)
                    job = wenv['shopify.connector.job'].browse(job_id)
                    client = wenv['shopify.connector.api.client']
                    with client.execute_business(
                            job, store, 'query { shop { id } }'):
                        pass
                except BaseException as exc:     # fail loud, sanitized (type-only)
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    self._safe_worker_teardown(wcr, diagnostics)

            Client = self.env['shopify.connector.api.client']
            got1 = got2 = False
            rows = None
            # DEADLOCK FIX (pre-existing, framework-level). Odoo's ThreadedServer
            # holds the reentrant `Registry._lock` for the ENTIRE preload /
            # post_install phase (service/server.py `run`: `with Registry._lock:
            # ... preload_registries()`, which runs this suite). A spawned worker's
            # `api.Environment(wcr, ...)` calls `Registry(cr.dbname)` ->
            # `Registry.__new__` -> `with cls._lock:`, which blocks forever on that
            # main-thread-held lock (a different thread cannot acquire it). The
            # single-threaded genuine tests above avoid this only because they build
            # the Environment in the MAIN thread, reentrantly reacquiring the lock it
            # already owns. Decouple the worker threads with a fresh registry lock
            # for the bounded window: the registry is fully built and stable here
            # (workers only do a cached read-only `registries[db_name]` lookup, never
            # a rebuild), so this preserves real mutual exclusion among the test
            # threads and weakens nothing — it is the same lock decoupling Odoo's own
            # `_registry_test_mode_patches` performs. Without it the REAL admission
            # code under test never even runs (workers die at Environment creation).
            with patch.object(type(self.registry), '_lock', threading.RLock()), \
                 patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', blocking_send):
                    t1 = threading.Thread(
                        target=worker, args=(job_ids[0],), daemon=True)
                    t2 = threading.Thread(
                        target=worker, args=(job_ids[1],), daemon=True)
                    t1.start()
                    t2.start()
                    try:
                        got1 = both_admitted.acquire(timeout=self.BOUND_SECONDS)
                        got2 = both_admitted.acquire(timeout=self.BOUND_SECONDS)
                        if got1 and got2:
                            # both leases coexist right now (workers parked at seam)
                            rows = self._committed_lease_rows(dbname, store_id)
                    finally:
                        # unblock, JOIN, and PROVE both dead BEFORE the patch is
                        # restored — a live worker must never run under the
                        # restored (shared test-cursor) registry factory.
                        release_gate.set()
                        t1.join(timeout=self.BOUND_SECONDS)
                        t2.join(timeout=self.BOUND_SECONDS)
                        self._assert_workers_dead((t1, t2))
            after = self._committed_lease_rows(dbname, store_id)

            # Sanitized worker findings first (surfaces any worker error as
            # type-only evidence), then the overlap/lease assertions.
            findings = self._drain(diagnostics)
            self.assertEqual(
                findings, [], 'sanitized worker findings: %s' % findings)
            self.assertTrue(
                got1 and got2, 'both real admissions did not overlap within bound')
            self.assertIsNotNone(rows, 'no coexisting-lease snapshot captured')
            self.assertEqual(len(rows), 2)                       # both committed
            self.assertEqual(len({r[0] for r in rows}), 2)       # distinct keys
            self.assertEqual({r[1] for r in rows}, set(job_ids))  # correct jobs
            self.assertEqual(len(after), 0)                      # both released
        finally:
            # repeat the termination guarantee after final joins, THEN clean up —
            # cleanup must never begin while a worker may still be live.
            release_gate.set()
            for t in (t1, t2):
                if t is not None:
                    t.join(timeout=self.BOUND_SECONDS)
            self._assert_workers_dead((t1, t2))
            self._cleanup(dbname, store_id, job_ids)

    # --- focused hardening tests (review 4681564744) -------------------

    # H1/H2. Every genuine cursor (worker main + production side, via the factory)
    # gets both transaction-local timeouts.
    def test_open_bounded_applies_both_timeouts(self):
        dbname = self.env.cr.dbname
        cr = self._open_bounded(dbname)
        try:
            cr.execute("SELECT current_setting('statement_timeout'), "
                       "current_setting('lock_timeout')")
            statement_timeout, lock_timeout = cr.fetchone()
            self.assertNotEqual(statement_timeout, '0')   # applied (non-default)
            self.assertNotEqual(lock_timeout, '0')        # applied (non-default)
            cr.rollback()
        finally:
            cr.close()
        # The patched registry factory routes through the same bounded helper.
        factory = self._real_registry_cursor(dbname)
        side = factory()
        try:
            side.execute("SELECT current_setting('statement_timeout'), "
                         "current_setting('lock_timeout')")
            st2, lt2 = side.fetchone()
            self.assertNotEqual(st2, '0')
            self.assertNotEqual(lt2, '0')
            side.rollback()
        finally:
            side.close()

    # H3. A failure while configuring a cursor closes that cursor.
    def test_open_bounded_closes_cursor_on_setup_failure(self):
        closed = []

        class _BoomCursor:
            def execute(self, *args, **kwargs):
                raise RuntimeError('boom during timeout setup')

            def close(self):
                closed.append(True)

        class _Conn:
            def cursor(self, *args, **kwargs):
                return _BoomCursor()

        mod = importlib.import_module(type(self).__module__)
        with patch.object(mod, 'db_connect', lambda *a, **k: _Conn()):
            with self.assertRaises(RuntimeError):
                self._open_bounded('anydb')
        self.assertEqual(closed, [True])   # the cursor was closed on failure

    # H4/H5. Worker rollback AND close failures both reach the parent as
    # SEPARATE, type-only sanitized findings — no raw text/SQL/paths/tokens.
    def test_worker_teardown_surfaces_sanitized_rollback_and_close(self):
        findings_q = queue.Queue()

        class _BadCursor:
            def rollback(self):
                raise RuntimeError('rollback boom /var/lib shpat_SECRET SELECT 1')

            def close(self):
                raise RuntimeError('close boom /etc token=shpat_SECRET DELETE')

        self._safe_worker_teardown(_BadCursor(), findings_q)
        findings = self._drain(findings_q)
        self.assertEqual({f['phase'] for f in findings},
                         {'rollback', 'cursor_close'})   # both, separately
        for finding in findings:
            self.assertEqual(finding['type'], 'RuntimeError')
            self.assertIsNone(finding['error_class'])
            blob = repr(finding)
            for leak in ('shpat_', 'SECRET', 'SELECT', 'DELETE', '/var', '/etc',
                         'boom', 'token'):
                self.assertNotIn(leak, blob)

    # H5b. _sanitize is strictly type-only, including for a connector error.
    def test_sanitize_is_type_only(self):
        exc = ShopifyClientError(
            error_class=ERROR_TEMPORARY,
            reason='secret shpat_LEAK', technical_detail='SELECT * secret /path')
        finding = self._sanitize(exc, 'worker_body')
        self.assertEqual(finding['phase'], 'worker_body')
        self.assertEqual(finding['type'], 'ShopifyClientError')
        self.assertEqual(finding['error_class'], ERROR_TEMPORARY)  # safe enum
        blob = repr(finding)
        for leak in ('shpat_', 'LEAK', 'SELECT', 'secret', '/path'):
            self.assertNotIn(leak, blob)

    # H6. The termination guarantee fails loudly on a live worker.
    def test_assert_workers_dead_fails_loud_on_live_worker(self):
        gate = threading.Event()
        thread = threading.Thread(target=gate.wait, daemon=True)
        thread.start()
        try:
            with self.assertRaises(AssertionError):
                self._assert_workers_dead((thread,))
        finally:
            gate.set()
            thread.join(timeout=self.BOUND_SECONDS)
        self._assert_workers_dead((thread,))   # now dead -> no raise

    # H7. The fresh zero-residue verifier checks job-log rows (and cleanup deletes
    # job logs before jobs). A runtime orphan job-log cannot exist (FK
    # ondelete='restrict'), so this guards the verifier/cleanup shape statically.
    def test_zero_residue_verifies_job_logs(self):
        residue_src = inspect.getsource(type(self)._assert_zero_residue)
        self.assertIn('shopify_connector_job_log', residue_src)
        self.assertIn('job-log residue after cleanup', residue_src)
        cleanup_src = inspect.getsource(type(self)._cleanup)
        self.assertIn('shopify_connector_job_log', cleanup_src)
        self.assertLess(
            cleanup_src.index('shopify_connector_job_log'),
            cleanup_src.index('DELETE FROM shopify_connector_job WHERE'),
            'job logs must be deleted before jobs (FK restrict)')


# ======================================================================
# CORE-R2 Foundation Slice 2A — disconnect lifecycle, quiescence
# controller, timeout finalization, credential-clear ordering.
#
# These classes exercise the Slice-2A production path: the two-phase
# `action_disconnect`, the `_run_disconnect_quiesce` controller + one-store
# selection, direction-C lease interpretation, `completed`/`timed_out`
# finalization + credential-clear ordering, and the delayed re-poll. The
# TransactionCase classes drive the real production methods (single
# connection); genuine cross-connection controller *selection* (locked-first
# / all-locked) is proven by `TestDisconnectControllerSelectionGenuine` using
# independent `db_connect` connections, mirroring `TestGenuineRealAdmission`.
# No live Shopify call, no lifecycle/state monkeypatch, no test-only timing
# hook (timeout is exercised by writing `disconnect_requested_at` -- a data
# value, not a clock fake).
# ======================================================================


class _DisconnectHelpers:
    """Shared fixtures/helpers for the Slice 2A tests (mixin, not a TestCase)."""

    def _make_store(self, state='connected', **vals):
        base = {
            'name': 'Disc Store',
            'shop_domain': 'disc-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': state,
        }
        base.update(vals)
        return self.env['shopify.connector.store'].create(base)

    def _connected_with_token(self):
        store = self._make_store(state='connected')
        # action_set_token demotes a connected store to reconnect_needed; re-
        # assert connected (the canonical fixture pattern used across the suite).
        self.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN
        )
        store.write({'state': 'connected'})
        return store

    def _credential(self, store):
        return self.env['shopify.connector.store.credential'].search(
            [('store_id', '=', store.id)], limit=1
        )

    def _disconnecting_store(self, requested_at=None, with_credential=False):
        store = (
            self._connected_with_token() if with_credential
            else self._make_store(state='connected')
        )
        store.write({
            'state': 'disconnecting',
            'disconnect_status': 'requested',
            'disconnect_requested_at': requested_at or fields.Datetime.now(),
        })
        return store

    def _make_lease(self, store, admitted_at=None, expires_at=None, job_id=1):
        now = fields.Datetime.now()
        return self.env['shopify.connector.call.lease'].create({
            'store_id': store.id,
            'lease_key': uuid.uuid4().hex,
            'job_id': job_id,
            'admitted_at': admitted_at or now,
            'expires_at': expires_at or (now + timedelta(seconds=300)),
        })

    def _lease_count(self, store):
        return self.env['shopify.connector.call.lease'].search_count(
            [('store_id', '=', store.id)]
        )

    def _audit_jobs(self, store):
        return self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_source', '=', 'setup_readiness_check'),
            ('job_type', '=', 'core_manual_maintenance'),
        ])

    def _disconnect_cron(self):
        return self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce'
        )

    def _cron_triggers(self, cron):
        return self.env['ir.cron.trigger'].search([('cron_id', '=', cron.id)])


class TestDisconnectPhase1(_DisconnectHelpers, TransactionCase):
    """Phase-1 two-phase `action_disconnect` + lifecycle request matrix.

    Controlled (single test connection). Review 4691182306 #1 made
    `_admit_lifecycle` capture its snapshot in an OWNED `registry.cursor()` side
    transaction (store-row FOR SHARE); registry test mode makes that side cursor a
    TestCursor sharing this test's connection so the in-test fixtures are visible
    cross-cursor (the mechanism `TestBusinessAdmission` uses for business
    `_admit`). Genuine cross-connection admission-vs-disconnect ordering is proven
    by `TestLifecycleAdmissionRaceGenuine`."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    # 1. connected -> disconnecting request (NOT disconnected; credential kept).
    def test_connected_moves_to_disconnecting(self):
        store = self._connected_with_token()
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'requested')
        self.assertTrue(store.disconnect_requested_at)
        self.assertEqual(store.disconnect_requested_by, self.env.user)
        # Credential is NOT cleared in Phase 1 (analysis §15).
        self.assertTrue(store.credential_present)
        self.assertTrue(self._credential(store).access_token)
        self.assertFalse(store.disconnect_completed_at)

    # 2. generation increments exactly once.
    def test_disconnect_bumps_generation_exactly_once(self):
        store = self._make_store(state='connected')
        self.assertEqual(store.connection_generation, 0)
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.connection_generation, 1)

    # 3. repeated disconnect is an audited idempotent no-op.
    def test_repeated_disconnect_is_audited_noop(self):
        store = self._make_store(state='connected')
        store.action_disconnect()
        store.invalidate_recordset()
        gen_after_first = store.connection_generation
        audits_after_first = len(self._audit_jobs(store))
        # Second call: no state change, NO second generation bump, one more
        # audited no-op.
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.connection_generation, gen_after_first)
        self.assertEqual(len(self._audit_jobs(store)), audits_after_first + 1)
        # A third call on an already-disconnected store is also a no-op.
        store.write({'state': 'disconnected'})
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.connection_generation, gen_after_first)

    # Phase-1 A/B sweep cancels queued/retry_waiting business jobs only.
    def test_phase1_sweeps_queued_and_retry_waiting_only(self):
        store = self._make_store(state='connected')
        Job = self.env['shopify.connector.job']
        queued = Job.create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })
        retry = Job.sudo().create({
            'store_id': store.id, 'job_source': 'webhook',
            'job_type': 'core_dispatch_selftest', 'state': 'retry_waiting',
            'payload_hash': uuid.uuid4().hex,
            'next_retry_at': fields.Datetime.now(), 'retry_count': 1,
        })
        store.action_disconnect()
        for job in (queued, retry):
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertEqual(job.cancel_reason, 'Store disconnecting.')

    # 18. Phase-1 sweep never writes a running/claimed business job row.
    def test_phase1_sweep_never_writes_running_job(self):
        store = self._make_store(state='connected')
        running = self.env['shopify.connector.job'].create({
            'store_id': store.id, 'job_source': 'scheduled_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'started_at': fields.Datetime.now(),
        })
        store.action_disconnect()
        running.invalidate_recordset()
        # The running row is not a sweep candidate (domain is queued/
        # retry_waiting) -> left untouched, never cancelled, never written.
        self.assertEqual(running.state, 'running')
        self.assertFalse(running.cancel_reason)

    # 19. disconnecting is non-startable for business jobs.
    def test_disconnecting_business_job_not_startable(self):
        store = self._make_store(state='connected')
        job = self.env['shopify.connector.job'].create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })
        # Move to disconnecting WITHOUT the Phase-1 sweep, so the job survives to
        # attempt a start.
        store.write({'state': 'disconnecting'})
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    # 20. action_test_connection is refused while disconnecting.
    def test_action_test_connection_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            store.action_test_connection()
        # No audit/test job was created by the refused attempt.
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_test_connection'),
        ]))

    # 20. _admit_lifecycle (PRIVATE -- no RPC-exposed purpose, reviews 4690639375
    # #2 + 4690804619 #1) enforces the purpose->state matrix and returns the one
    # credential snapshot: `disconnecting` refuses every purpose; `test_connection`
    # excludes `disconnected`; `reconnect_probe` permits it.
    def test_admit_lifecycle_private_matrix_enforcement(self):
        Client = self.env['shopify.connector.api.client']
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'test_connection')
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'reconnect_probe')
        # Unknown purpose fails closed.
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'not_a_purpose')
        # test_connection excludes `disconnected`; reconnect_probe permits it.
        store.write({'state': 'disconnected'})
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'test_connection')
        # reconnect_probe from disconnected passes the matrix and returns a
        # one-token snapshot (no transport needed for the gate).
        snapshot = Client._admit_lifecycle(store, 'reconnect_probe')
        self.assertEqual(snapshot['token'], DUMMY_TOKEN)
        self.assertEqual(
            snapshot['allowed_states'], ('reconnect_needed', 'disconnected'))

    # The purpose-carrying lifecycle entries are PRIVATE (not RPC-exposed); the
    # former `_execute_lifecycle` was split into `_admit_lifecycle`/`_send_lifecycle`.
    def test_lifecycle_helpers_are_private(self):
        Client = type(self.env['shopify.connector.api.client'])
        self.assertTrue(hasattr(Client, '_admit_lifecycle'))
        self.assertTrue(hasattr(Client, '_send_lifecycle'))
        self.assertFalse(hasattr(Client, 'execute_lifecycle'))
        self.assertFalse(hasattr(Client, '_execute_lifecycle'))

    # Activation and reconnect lifecycle operations are refused during
    # disconnecting (matrix §8).
    def test_activate_and_reconnect_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            store.action_activate()
        with self.assertRaises(UserError):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')

    # A successful activation bumps the generation exactly once (matrix §8).
    def test_activation_bumps_generation(self):
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        now = fields.Datetime.now()
        store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': now,
            'last_readiness_at': now,
        })
        gen_before = store.connection_generation
        store.action_activate()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')
        self.assertEqual(store.connection_generation, gen_before + 1)


class TestQuiescenceController(_DisconnectHelpers, TransactionCase):
    """The `_run_disconnect_quiesce` controller + direction-C finalization."""

    # 5 / 23. zero leases -> completed -> credential cleared -> disconnected.
    def test_zero_leases_completes_clears_credential(self):
        store = self._connected_with_token()
        store.action_disconnect()                    # -> disconnecting
        self.assertEqual(self._lease_count(store), 0)
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertTrue(store.disconnect_completed_at)
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)
        self.assertEqual(self._credential(store).credential_state, 'absent')

    # 4. credential remains present while leases exist before timeout.
    def test_credential_present_while_leases_before_timeout(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertTrue(store.credential_present)
        self.assertTrue(self._credential(store).access_token)

    # 6. one live lease -> quiescing, no credential clear, snapshot written.
    def test_one_live_lease_quiescing(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertEqual(store.disconnect_open_lease_count, 1)
        self.assertTrue(store.disconnect_oldest_admitted_at)
        self.assertTrue(store.credential_present)

    # 7. one EXPIRED, unreleased lease still -> quiescing before timeout
    # (direction C: expired = unknown/live, still counts).
    def test_expired_lease_still_quiescing_before_timeout(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        now = fields.Datetime.now()
        self._make_lease(
            store,
            admitted_at=now - timedelta(seconds=600),
            expires_at=now - timedelta(seconds=1),      # already expired
        )
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertEqual(store.disconnect_open_lease_count, 1)
        self.assertTrue(store.credential_present)       # never reaped -> no clear
        self.assertNotEqual(store.disconnect_status, 'completed')

    # 8 / 24. lease rows at the deadline -> timed_out, never completed, distinct.
    def test_leases_at_deadline_timed_out(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'timed_out')
        self.assertEqual(store.state, 'disconnected')
        self.assertNotEqual(store.disconnect_status, 'completed')

    # 9. timed_out finalization clears the credential.
    def test_timed_out_clears_credential(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    # 10. timed_out lease cleanup occurs ONLY AFTER finalization.
    def test_timed_out_cleans_leases_only_after_finalize(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        self._make_lease(store, job_id=2)
        self.assertEqual(self._lease_count(store), 2)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        # Snapshot recorded the outstanding count BEFORE cleanup...
        self.assertEqual(store.disconnect_open_lease_count, 2)
        self.assertEqual(store.disconnect_status, 'timed_out')
        # ...and the residual rows are cleaned up only after timed_out finalize.
        self.assertEqual(self._lease_count(store), 0)

    # 23. `completed` requires exactly zero lease rows.
    def test_completed_requires_zero_lease_rows(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertNotEqual(store.disconnect_status, 'completed')
        self.assertNotEqual(store.state, 'disconnected')

    # 11 / 12. still-quiescing store schedules a DELAYED re-poll
    # (at >= now + POLL_DELAY), never an immediate/busy re-trigger.
    def test_quiescing_schedules_delayed_repoll(self):
        store = self._disconnecting_store(requested_at=fields.Datetime.now())
        self._make_lease(store)
        cron = self._disconnect_cron()
        self._cron_triggers(cron).unlink()          # isolate this pass's trigger
        before = fields.Datetime.now()
        store._process_disconnect_quiesce()
        after = fields.Datetime.now()
        triggers = self._cron_triggers(cron)
        self.assertTrue(triggers, 'a delayed re-poll trigger must be scheduled')
        for trig in triggers:
            # delayed by >= POLL_DELAY (no immediate same-store re-trigger)...
            self.assertGreaterEqual(trig.call_at, before + POLL_DELAY)
            # ...and not further out than one POLL_DELAY from this pass.
            self.assertLessEqual(
                trig.call_at, after + POLL_DELAY + timedelta(seconds=5)
            )

    # 14. exactly one store is processed per controller invocation.
    def test_one_store_per_invocation(self):
        now = fields.Datetime.now()
        store_a = self._disconnecting_store(
            requested_at=now - timedelta(seconds=20)     # older -> selected first
        )
        store_b = self._disconnecting_store(
            requested_at=now - timedelta(seconds=5)
        )
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store_a.invalidate_recordset()
        store_b.invalidate_recordset()
        self.assertEqual(store_a.state, 'disconnected')  # processed (0 leases)
        self.assertEqual(store_b.state, 'disconnecting')  # untouched this pass

    # 16. duplicate controller invocation is idempotent (no double-finalize).
    def test_controller_duplicate_invocation_idempotent(self):
        store = self._connected_with_token()
        store.action_disconnect()
        Controller = self.env['shopify.connector.store']
        Controller._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'completed')
        completed_at = store.disconnect_completed_at
        audits_before = len(self._audit_jobs(store))
        # A second pass must not re-finalize the now-disconnected store.
        Controller._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertEqual(store.disconnect_completed_at, completed_at)
        self.assertEqual(len(self._audit_jobs(store)), audits_before)

    # 22. no token/credential enters the disconnect status/snapshot/audit.
    def test_no_secret_in_disconnect_fields_and_audit(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()            # -> timed_out, snapshot
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'timed_out')
        # Store char/text fields carry no token...
        for fname, field in store._fields.items():
            if field.type in ('char', 'text') and store[fname]:
                self.assertNotIn(DUMMY_TOKEN, store[fname])
        # ...nor do the audit jobs/logs for this store.
        jobs = self.env['shopify.connector.job'].search(
            [('store_id', '=', store.id)]
        )
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', 'in', jobs.ids)]
        )
        for recs in (jobs, logs):
            for rec in recs:
                for fname, field in rec._fields.items():
                    if field.type in ('char', 'text') and rec[fname]:
                        self.assertNotIn(DUMMY_TOKEN, rec[fname])


class TestDisconnectSourceGuards(_DisconnectHelpers, TransactionCase):
    """Source-level guards for the Slice 2A store controller/lifecycle."""

    # 17. No explicit request/main-cursor commit anywhere in the store model.
    def test_no_main_cursor_commit_in_store_source(self):
        src = inspect.getsource(store_module)
        self.assertNotIn('self.env.cr.commit', src)
        self.assertNotIn('self._cr.commit', src)
        self.assertNotIn('self.env.cr.rollback', src)
        self.assertNotIn('.commit()', src)

    # Controller selection is the corrected FOR UPDATE SKIP LOCKED LIMIT 1.
    def test_controller_uses_skip_locked_limit_one(self):
        src = inspect.getsource(
            store_module.ShopifyConnectorStore._run_disconnect_quiesce
        )
        self.assertIn('try_lock_for_update(limit=1)', src)

    # The generation-changing lifecycle lock is a BLOCKING FOR NO KEY UPDATE
    # (never SKIP LOCKED -- a lifecycle transition must wait, not be skipped).
    def test_lifecycle_lock_is_blocking_for_no_key_update(self):
        # AST-robust (control-room review 4692156428): inspect the SQL string
        # literal actually passed to `.execute(...)` in the executable body, so
        # the method docstring's "unlike ... FOR UPDATE SKIP LOCKED" prose is
        # NOT a false positive. The lifecycle lock must be a blocking FOR NO KEY
        # UPDATE and must NEVER use SKIP LOCKED in real SQL.
        fn = guard_fn_ast(
            store_module.ShopifyConnectorStore._lock_store_for_lifecycle)
        sql = guard_execute_sql(fn)
        self.assertIn('FOR NO KEY UPDATE', sql)
        self.assertNotIn('SKIP LOCKED', sql)

    # Delayed re-poll uses _trigger(at=...); no immediate same-store re-trigger
    # from a quiescing pass; no busy loop / sleep anywhere.
    def test_delayed_repoll_and_no_busy_loop(self):
        proc_src = inspect.getsource(
            store_module.ShopifyConnectorStore._process_disconnect_quiesce
        )
        self.assertIn('POLL_DELAY', proc_src)
        trig_src = inspect.getsource(
            store_module.ShopifyConnectorStore._trigger_disconnect_controller
        )
        self.assertIn('_trigger(at=at)', trig_src)
        module_src = inspect.getsource(store_module)
        self.assertNotIn('while True', module_src)
        self.assertNotIn('time.sleep', module_src)
        self.assertNotIn('import time', module_src)

    # 21. Credential clear follows the store -> credential lock order: the
    # controller takes the store FOR UPDATE (selection) BEFORE any finalize calls
    # the controller-only PRIVATE clear primitive; it must NOT call the public
    # action_clear_token (which refuses a `disconnecting` store); Phase 1 never
    # clears the credential (review 4690804619 #2).
    def test_store_then_credential_clear_order(self):
        # AST-robust (control-room review 4692156428): inspect executable call
        # nodes, so `_finalize_disconnect_completed`'s docstring "never the
        # public `action_clear_token`" prose is NOT a false positive. Both
        # finalizers must call the controller-only PRIVATE clear primitive and
        # must NEVER call the public `action_clear_token` (which refuses a
        # `disconnecting` store); the controller selects under
        # `try_lock_for_update(limit=1)`; Phase 1 clears nothing.
        controller = guard_fn_ast(
            store_module.ShopifyConnectorStore._run_disconnect_quiesce)
        self.assertTrue(
            guard_has_call_with_const_kwarg(
                controller, 'try_lock_for_update', 'limit', 1),
            'controller must select via try_lock_for_update(limit=1)')
        for name in (
            '_finalize_disconnect_completed', '_finalize_disconnect_timed_out',
        ):
            called = guard_called_names(
                guard_fn_ast(getattr(store_module.ShopifyConnectorStore, name)))
            self.assertIn('_clear_token_under_store_lock', called)
            self.assertNotIn('action_clear_token', called)
        phase1 = guard_called_names(
            guard_fn_ast(store_module.ShopifyConnectorStore.action_disconnect))
        self.assertNotIn('action_clear_token', phase1)
        self.assertNotIn('_clear_token_under_store_lock', phase1)

    # The controller / finalization make NO Shopify call.
    def test_controller_makes_no_shopify_call(self):
        for name in (
            '_run_disconnect_quiesce', '_process_disconnect_quiesce',
            '_finalize_disconnect_completed', '_finalize_disconnect_timed_out',
        ):
            src = inspect.getsource(
                getattr(store_module.ShopifyConnectorStore, name)
            )
            for forbidden in (
                '_send', 'requests', '.execute(', 'execute_business',
                'execute_lifecycle',
            ):
                self.assertNotIn(forbidden, src)


@tagged('post_install', '-at_install')
class TestDisconnectControllerSelectionGenuine(TransactionCase):
    """Genuine cross-connection controller selection (proofs 13 + 15).

    A locked first store must not block a later unlocked one, and an all-locked
    set must be a safe no-op. Both need a *second* connection to hold a real
    row lock, so this uses independent `db_connect` connections (mirroring
    `TestGenuineRealAdmission`): fixtures are committed on a bounded connection,
    one/both stores are locked `FOR UPDATE` on a second bounded connection, the
    real `_run_disconnect_quiesce` runs on a worker connection, results are
    observed on a fresh connection, and teardown is bounded + fail-loud.
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000

    def _open_bounded(self, dbname):
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _commit_two_disconnecting_stores(self, dbname):
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            now = fields.Datetime.now()
            ids = []
            # store_a is the OLDER request -> ordered first by the controller.
            for offset in (20, 5):
                store = env['shopify.connector.store'].create({
                    'name': 'Genuine Disc Store',
                    'shop_domain': 'genuine-disc-%s.myshopify.com'
                    % uuid.uuid4().hex,
                    'api_version': '2026-07',
                    'state': 'disconnecting',
                    'disconnect_status': 'requested',
                    'disconnect_requested_at': now - timedelta(seconds=offset),
                })
                env['shopify.connector.call.lease'].create({
                    'store_id': store.id,
                    'lease_key': uuid.uuid4().hex,
                    'job_id': 1,
                    'admitted_at': now,
                    'expires_at': now + timedelta(seconds=300),
                })
                ids.append(store.id)
            setup.commit()
            return ids
        finally:
            setup.close()

    def _status(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT disconnect_status FROM shopify_connector_store "
                "WHERE id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _cleanup(self, dbname, store_ids):
        if not store_ids:
            return
        cr = self._open_bounded(dbname)
        try:
            cr.execute(
                "DELETE FROM ir_cron_trigger WHERE cron_id IN "
                "(SELECT res_id FROM ir_model_data WHERE module = "
                "'shopify_connector_core' AND name = "
                "'ir_cron_shopify_connector_disconnect_quiesce')")
            cr.execute(
                "DELETE FROM shopify_connector_call_lease "
                "WHERE store_id = ANY(%s)", (list(store_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = ANY(%s)",
                (list(store_ids),))
            cr.commit()
        finally:
            cr.close()
        verifier = self._open_bounded(dbname)
        try:
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_store "
                "WHERE id = ANY(%s)", (list(store_ids),))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'store residue after cleanup')
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = ANY(%s)", (list(store_ids),))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'lease residue after cleanup')
            verifier.rollback()
        finally:
            verifier.close()

    def _run_controller_worker(self, dbname):
        worker = self._open_bounded(dbname)
        try:
            wenv = api.Environment(worker, SUPERUSER_ID, {})
            wenv['shopify.connector.store']._run_disconnect_quiesce()
            worker.commit()
        finally:
            worker.close()

    # 13. A locked first store does not block a later unlocked store.
    def test_locked_first_store_does_not_block_later(self):
        dbname = self.env.cr.dbname
        store_ids = []
        lock_cr = None
        try:
            store_ids = self._commit_two_disconnecting_stores(dbname)
            id_a, id_b = store_ids
            # Hold FOR UPDATE on the FIRST (older) store on an independent
            # connection.
            lock_cr = self._open_bounded(dbname)
            lock_cr.execute(
                "SELECT id FROM shopify_connector_store WHERE id = %s "
                "FOR UPDATE", (id_a,))
            lock_cr.fetchone()
            # The controller must skip the locked A and process B.
            self._run_controller_worker(dbname)
            self.assertEqual(self._status(dbname, id_b), 'quiescing')  # processed
            self.assertEqual(self._status(dbname, id_a), 'requested')  # skipped
        finally:
            if lock_cr is not None:
                lock_cr.rollback()
                lock_cr.close()
            self._cleanup(dbname, store_ids)

    # 15. All eligible stores locked -> the controller is a safe no-op.
    def test_all_locked_is_safe_noop(self):
        dbname = self.env.cr.dbname
        store_ids = []
        lock_cr = None
        try:
            store_ids = self._commit_two_disconnecting_stores(dbname)
            lock_cr = self._open_bounded(dbname)
            lock_cr.execute(
                "SELECT id FROM shopify_connector_store WHERE id = ANY(%s) "
                "FOR UPDATE", (list(store_ids),))
            lock_cr.fetchall()
            # Every eligible row is locked -> this pass processes nothing.
            self._run_controller_worker(dbname)
            for sid in store_ids:
                self.assertEqual(self._status(dbname, sid), 'requested')
        finally:
            if lock_cr is not None:
                lock_cr.rollback()
                lock_cr.close()
            self._cleanup(dbname, store_ids)


class TestLifecycleRaceCorrections(_DisconnectHelpers, TransactionCase):
    """CORE-R2 review 4690639375 #1/#2: activation/reconnect TOCTOU + the
    reconnect_probe path. Controlled tests driving the REAL production
    `action_activate`/`action_reconnect`; the racing disconnect is a genuine
    `action_disconnect` injected at the sanctioned `_send` transport seam (never
    a lifecycle/state monkeypatch). Single test connection: registry test mode
    makes the `_admit_lifecycle` side cursor (review 4691182306 #1) a TestCursor
    sharing this connection so the in-test fixtures are visible cross-cursor."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _seed_activation_evidence(self, store):
        now = fields.Datetime.now()
        store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': now,
            'last_readiness_at': now,
        })

    def _fake_readiness_pass(self):
        def fake_run_for_store(rc_self, store):
            store.write({
                'last_readiness_result': 'pass',
                'last_readiness_at': fields.Datetime.now(),
            })
            return {'job': None, 'overall_result': 'pass', 'checks': []}
        return fake_run_for_store

    # Activation must refuse a store a disconnect already won, without a second
    # generation bump and without an activation audit (TOCTOU-safe under lock).
    def test_activation_refuses_when_disconnect_won(self):
        store = self._connected_with_token()
        self._seed_activation_evidence(store)
        store.action_disconnect()                    # -> disconnecting, gen +1
        store.invalidate_recordset()
        gen_after_disconnect = store.connection_generation
        audits_before = len(self._audit_jobs(store))
        with self.assertRaises(UserError):
            store.action_activate()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')          # not overwritten
        self.assertEqual(
            store.connection_generation, gen_after_disconnect)  # no 2nd bump
        self.assertEqual(
            len(self._audit_jobs(store)), audits_before)        # no activation audit

    # Reconnect must refuse to overwrite a disconnect that won DURING the probe.
    def test_reconnect_refuses_when_disconnect_wins_during_probe(self):
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        store.invalidate_recordset()
        gen_before = store.connection_generation
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']

        def racing_send(client_self, store_arg, body, token=None):
            # A REAL one-way disconnect wins the race during the probe's call.
            store.action_disconnect()
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        with patch.object(type(Client), '_send', racing_send), \
             patch.object(type(ReadinessCheck), 'run_for_store',
                          self._fake_readiness_pass()):
            store.action_reconnect()
        store.invalidate_recordset()
        # Disconnect won -> reconnect must NOT overwrite it.
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'requested')
        # Only the injected disconnect bumped the epoch (+1); reconnect bumped none.
        self.assertEqual(store.connection_generation, gen_before + 1)

    # Reconnect from a completed `disconnected` store (unchanged epoch) succeeds
    # via reconnect_probe -- NOT refused by a blanket `disconnected` check.
    def test_reconnect_from_disconnected_connects(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnected'})
        store.invalidate_recordset()
        gen_before = store.connection_generation
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']

        def ok_send(client_self, store_arg, body, token=None):
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        with patch.object(type(Client), '_send', ok_send), \
             patch.object(type(ReadinessCheck), 'run_for_store',
                          self._fake_readiness_pass()):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')
        self.assertEqual(store.connection_generation, gen_before + 1)


class TestLifecycleProbeSupersession(_DisconnectHelpers, TransactionCase):
    """CORE-R2 reviews 4690804619 #1 + 4691182306: the lifecycle probe binds to
    ONE credential snapshot (single token read, credential id/version, store
    generation), issues the request with exactly that token via
    `_send(store, body, token)`, and after the network result revalidates
    state/generation/credential id+version+value under the store->credential
    locks. A lifecycle or credential change that wins DURING the probe must be
    detected: the response is discarded, the probe job is audited `cancelled`
    ('superseded'), and NO verification/failure mirror or credential state is
    written.

    **Controlled seam-injection tests, NOT genuine concurrency (review
    4691182306 #2).** The racing change is injected at the sanctioned `_send`
    transport seam within a single test connection; registry test mode makes the
    `_admit_lifecycle` side cursor (review 4691182306 #1) a TestCursor sharing that
    connection, so these prove the snapshot/revalidation LOGIC but not
    distinct-backend independence. Genuine cross-connection admission-vs-disconnect
    ordering (both orders, distinct PIDs) is proven by
    `TestLifecycleAdmissionRaceGenuine`."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _probe_job(self, store):
        return self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_test_connection'),
        ], order='id desc', limit=1)

    def _run_probe(self, store, send_fake):
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', send_fake):
            store.action_test_connection()

    def _replace_during_send(self, store, new_token):
        def racing_send(client_self, s, body, token=None):
            self.env['shopify.connector.store.credential'].action_replace_token(
                store, new_token)
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))
        return racing_send

    def test_send_lifecycle_receives_exact_snapshot_token(self):
        # Review §4: the request uses EXACTLY the admitted snapshot token -- the
        # transport is handed the token, never left to re-read the credential.
        store = self._connected_with_token()
        captured = {}

        def spy_send(client_self, s, body, token=None):
            captured['token'] = token
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, spy_send)
        self.assertEqual(captured.get('token'), DUMMY_TOKEN)

    def test_probe_not_superseded_applies_pass_mirror(self):
        # Snapshot unchanged through the probe -> the result is applied normally
        # (guards against a false-positive supersede).
        store = self._connected_with_token()

        def ok_send(client_self, s, body, token=None):
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, ok_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(store.last_test_connection_result, 'pass')
        self.assertTrue(store.credential_last_verified_at)

    def test_test_connection_superseded_by_credential_replace(self):
        # A connected replace bumps the epoch -> generation mismatch supersedes.
        store = self._connected_with_token()
        self._run_probe(store, self._replace_during_send(store, DUMMY_TOKEN + 'N'))
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        # No pass mirror / verification stamp written from the stale result.
        self.assertNotEqual(store.last_test_connection_result, 'pass')
        self.assertFalse(store.credential_last_verified_at)

    def test_test_connection_superseded_by_disconnect(self):
        store = self._connected_with_token()

        def racing_send(client_self, s, body, token=None):
            store.action_disconnect()
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, racing_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        self.assertEqual(store.state, 'disconnecting')
        self.assertNotEqual(store.last_test_connection_result, 'pass')

    def test_auth_failure_superseded_does_not_invalidate_replaced_token(self):
        # The exact hazard review 4690804619 #1 names: an OLD-token failure must
        # not invalidate a token that was REPLACED during the probe.
        store = self._connected_with_token()

        def racing_send(client_self, s, body, token=None):
            self.env['shopify.connector.store.credential'].action_replace_token(
                store, DUMMY_TOKEN + 'N')
            return FakeResponse(200, json_body={
                'errors': [{
                    'message': 'Access denied',
                    'extensions': {'code': 'ACCESS_DENIED'},
                }],
            })

        self._run_probe(store, racing_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        # Superseded -> cancelled, NOT failed_final; the new token is intact.
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        credential = self._credential(store)
        self.assertEqual(credential.access_token, DUMMY_TOKEN + 'N')
        self.assertNotEqual(credential.credential_state, 'invalid')

    def test_reconnect_superseded_by_credential_replace_aborts(self):
        # A reconnect_needed replace does NOT bump the epoch, so the credential
        # value revalidation is what supersedes; the reconnect then aborts BEFORE
        # readiness / finalize.
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        store.invalidate_recordset()
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']
        readiness_calls = []

        def fake_readiness(rc_self, s):
            readiness_calls.append(s.id)
            return {'job': None, 'overall_result': 'pass', 'checks': []}

        with patch.object(
            type(Client), '_send',
            self._replace_during_send(store, DUMMY_TOKEN + 'N'),
        ), patch.object(
            type(ReadinessCheck), 'run_for_store', fake_readiness
        ):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(readiness_calls, [])          # aborted before readiness
        self.assertNotEqual(store.state, 'connected')
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)


class TestCredentialClearPolicy(_DisconnectHelpers, TransactionCase):
    """CORE-R2 reviews 4690804619 #2 + 4690807427: the public/manual credential
    clear never bypasses two-phase quiescence. A live/recoverable store routes
    through `action_disconnect` and is cleared only by the controller at
    `completed`/`timed_out`; `disconnecting` is refused; only setup_incomplete /
    disconnected clear directly. An admitted lease keeps the credential present
    until the controller observes zero holders (no premature clear).

    **Controlled tests, NOT genuine concurrency (review 4691182306 #2).** These
    drive the REAL `action_clear_token`/`action_disconnect`/controller on a single
    test connection with a synthetic committed lease row; they prove the
    clear-policy LOGIC and the state/credential/generation sequence, but not
    distinct-backend independence. None of them opens a side cursor (no
    `_admit_lifecycle`), so registry test mode is unnecessary here. Genuine
    cross-connection public-clear-vs-business-admission ordering (both orders,
    distinct PIDs, real committed `execute_business` lease) is proven by
    `TestPublicClearAdmissionRaceGenuine`."""

    def test_public_clear_connected_defers_to_controller_no_premature_clear(self):
        # The linearization proof: a public clear on a connected store with an
        # outstanding committed lease must NOT clear the credential until the
        # controller reaches `completed` (zero holders).
        store = self._connected_with_token()
        lease = self._make_lease(store)
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        # Two-phase requested; credential still present while the lease is open.
        self.assertEqual(store.state, 'disconnecting')
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

        # Controller pass with the lease still open -> quiescing, still not cleared.
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

        # Holder releases -> next controller pass finalizes and clears then.
        lease.unlink()
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_public_clear_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        with self.assertRaises(UserError):
            self.env['shopify.connector.store.credential'].action_clear_token(
                store)
        store.invalidate_recordset()
        # Credential untouched by the refused clear.
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

    def test_public_clear_direct_from_setup_incomplete(self):
        store = self._make_store(state='setup_incomplete')
        self.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN)
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        self.assertEqual(store.state, 'setup_incomplete')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_public_clear_direct_from_disconnected(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnected'})
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_action_disconnect_uses_locked_generation_directly(self):
        # Review §11: the Phase-1 write bumps to locked_generation + 1 from the
        # value returned under the lock (exactly one bump).
        store = self._connected_with_token()
        store.invalidate_recordset()
        gen_before = store.connection_generation
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.connection_generation, gen_before + 1)


@tagged('post_install', '-at_install')
class TestCredentialReplacementRaceGenuine(TransactionCase):
    """CORE-R2 review 4690639375 #3 (§6.8/§6.9): genuine admission-vs-replacement
    linearization through the REAL `execute_business`/`_admit` boundary and the
    REAL `action_replace_token`, on independent `db_connect` connections (the
    production `_admit` side transaction is made genuinely independent by patching
    the registry cursor factory for the bounded window, mirroring
    `TestGenuineRealAdmission`). Raw SQL is used only for observation/cleanup."""

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    NEW_TOKEN = 'shpat_DUMMYDUMMYDUMMY2222222222222222'

    def _open_bounded(self, dbname):
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _real_registry_cursor(self, dbname):
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _commit_connected_fixture(self, dbname):
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Cred Race Store',
                'shop_domain': 'cred-race-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            job = env['shopify.connector.job.enqueue'].enqueue(
                store, 'manual_sync', 'core_dispatch_selftest',
                payload_hash=uuid.uuid4().hex,
            )
            ids = (store.id, job.id)
            setup.commit()
            return ids
        finally:
            setup.close()

    def _observe(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, connection_generation FROM "
                "shopify_connector_store WHERE id = %s", (store_id,))
            store_row = obs.fetchone()
            obs.execute(
                "SELECT access_token FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cred_row = obs.fetchone()
            obs.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            lease_count = obs.fetchone()[0]
            obs.rollback()
            return store_row, cred_row, lease_count
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id, job_id):
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            if job_id is not None:
                cr.execute(
                    "DELETE FROM shopify_connector_job_log WHERE job_id = %s",
                    (job_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            if job_id is not None:
                cr.execute(
                    "DELETE FROM shopify_connector_job WHERE id = %s", (job_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        verifier = self._open_bounded(dbname)
        try:
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'store residue after cleanup')
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'lease residue after cleanup')
            verifier.rollback()
        finally:
            verifier.close()

    # 6.9. Replacement winning FIRST: an old-generation admission fails closed
    # and never captures the newly-replaced token.
    def test_replacement_first_old_generation_admission_fails_closed(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        try:
            store_id, job_id = self._commit_connected_fixture(dbname)
            # Replacement commits first on an independent connection: connected ->
            # reconnect_needed, generation bumped, new token stored.
            repl = self._open_bounded(dbname)
            try:
                renv = api.Environment(repl, SUPERUSER_ID, {})
                renv['shopify.connector.store.credential'].action_replace_token(
                    renv['shopify.connector.store'].browse(store_id),
                    self.NEW_TOKEN,
                )
                repl.commit()
            finally:
                repl.close()
            # The old-generation admission now runs against the committed replace.
            worker = self._open_bounded(dbname)
            captured = {}
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def spy_send(client_self, s, b, token=None):
                    captured['token'] = token
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', spy_send):
                        with self.assertRaises(ShopifyQuiescedError):
                            with Client.execute_business(job, store, 'q'):
                                pass
                worker.rollback()
            finally:
                worker.close()
            # Fail-closed: no _send, so the new token was never captured...
            self.assertNotIn('token', captured)
            # ...and no lease was committed for the refused admission.
            _store_row, cred_row, lease_count = self._observe(dbname, store_id)
            self.assertEqual(lease_count, 0)
            self.assertEqual(cred_row[0], self.NEW_TOKEN)   # replace won
        finally:
            self._cleanup(dbname, store_id, job_id)

    # 6.8. Admission FIRST: it commits its lease and captures the OLD token; a
    # replacement during the call proceeds afterward and the in-flight call keeps
    # its captured old token (single in-memory snapshot).
    def test_admission_first_uses_old_token_then_replacement_proceeds(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        try:
            store_id, job_id = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            captured = {}
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, b, token=None):
                    # The lease is already committed (old gen, old token captured)
                    # before _send. A replacement now runs on an INDEPENDENT
                    # connection; it does not block (admission's FOR SHARE already
                    # released) and bumps the epoch.
                    captured['token'] = token
                    repl = self._open_bounded(dbname)
                    try:
                        renv = api.Environment(repl, SUPERUSER_ID, {})
                        renv[
                            'shopify.connector.store.credential'
                        ].action_replace_token(
                            renv['shopify.connector.store'].browse(store_id),
                            self.NEW_TOKEN,
                        )
                        repl.commit()
                    finally:
                        repl.close()
                    captured['lease_during'] = self._observe(dbname, store_id)[2]
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', racing_send):
                        with Client.execute_business(job, store, 'q') as result:
                            self.assertEqual(result['data'], {})
                worker.rollback()
            finally:
                worker.close()
            # The admitted call used its captured OLD token, never the replacement.
            self.assertEqual(captured['token'], DUMMY_TOKEN)
            self.assertEqual(captured['lease_during'], 1)   # lease held during call
            store_row, cred_row, lease_count = self._observe(dbname, store_id)
            self.assertEqual(cred_row[0], self.NEW_TOKEN)   # replace proceeded
            self.assertEqual(store_row[0], 'reconnect_needed')
            self.assertEqual(lease_count, 0)                # released on exit
        finally:
            self._cleanup(dbname, store_id, job_id)


class TestLifecycleAdmissionSourceGuards(TransactionCase):
    """CORE-R2 review 4691182306 #1 -- source guards for the ATOMIC lifecycle
    admission: `_admit_lifecycle` captures its snapshot in a short OWNED side
    transaction (store-row FOR SHARE) that commits/closes BEFORE the network call,
    creates NO call lease, hands the exact snapshot token to the transport, and its
    result still flows through the post-network revalidation. These are pure source
    assertions (no side cursor); genuine behaviour is proven by
    `TestLifecycleAdmissionRaceGenuine`."""

    def _admit_src(self):
        return inspect.getsource(
            client_module.ShopifyConnectorApiClient._admit_lifecycle)

    def _probe_src(self):
        return inspect.getsource(
            store_module.ShopifyConnectorStore._run_connection_probe)

    def test_admit_lifecycle_owns_a_side_cursor(self):
        src = self._admit_src()
        self.assertIn('self.env.registry.cursor()', src)
        self.assertIn('side_cr', src)

    def test_admit_lifecycle_executes_store_for_share(self):
        src = self._admit_src()
        self.assertIn('FOR SHARE', src)
        self.assertIn('FROM shopify_connector_store', src)

    def test_admit_lifecycle_fresh_matrix_check_under_lock(self):
        # The matrix state check reads the value returned by the FOR SHARE SELECT
        # (fresh under the lock), not a cached `store.state`.
        src = self._admit_src()
        self.assertIn('state, generation = row', src)
        self.assertIn('if state not in allowed_states:', src)

    def test_admit_lifecycle_single_token_read_under_lock(self):
        src = self._admit_src()
        self.assertEqual(src.count('_get_access_token('), 1)

    def test_admit_lifecycle_only_side_cursor_commit_and_rollback(self):
        src = self._admit_src()
        self.assertIn('side_cr.commit()', src)
        self.assertIn('side_cr.rollback()', src)
        self.assertNotIn('self.env.cr.commit', src)
        self.assertNotIn('self._cr.commit', src)
        committed = re.findall(r'(\w+)\.commit\(\)', src)
        self.assertTrue(committed)
        self.assertTrue(all(name == 'side_cr' for name in committed),
                        'only the owned side cursor may commit; found %s' % committed)
        rolled = re.findall(r'(\w+)\.rollback\(\)', src)
        self.assertTrue(all(name == 'side_cr' for name in rolled),
                        'only the owned side cursor may rollback; found %s' % rolled)

    def test_admit_lifecycle_creates_no_lease(self):
        # AST-robust (control-room review 4692156428): inspect the executable
        # body, so the `_admit_lifecycle` docstring's "no `call.lease` is
        # created" prose is NOT a false positive. The lifecycle admission must
        # create no lease -- no lease-model lookup, no `lease_key` identifier,
        # and no create() call anywhere in real code.
        fn = guard_fn_ast(
            client_module.ShopifyConnectorApiClient._admit_lifecycle)
        self.assertNotIn(
            'shopify.connector.call.lease', guard_str_constants(fn))
        self.assertNotIn('lease_key', guard_identifiers(fn))
        self.assertNotIn('create', guard_called_names(fn))

    def test_admit_lifecycle_commits_and_closes_before_transport(self):
        # The side transaction commits and the cursor closes INSIDE
        # `_admit_lifecycle`; the transport (`_send_lifecycle`) is a SEPARATE call
        # in `_run_connection_probe` that runs only AFTER `_admit_lifecycle`
        # returns -> no lock spans the network call.
        src = self._admit_src()
        self.assertIn('side_cr.commit()', src)
        self.assertIn('side_cr.close()', src)
        self.assertLess(src.index('side_cr.commit()'), src.index('return snapshot'))
        # No transport CALL inside the admission (the FOR SHARE must not span the
        # network). Inspect actual call nodes, so a docstring mention of
        # `_send_lifecycle` is NOT a false positive.
        fn = ast.parse(textwrap.dedent(src)).body[0]
        called = {
            n.func.attr for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertNotIn('_send', called)
        self.assertNotIn('_send_lifecycle', called)
        probe = self._probe_src()
        self.assertLess(
            probe.index('_admit_lifecycle'), probe.index('_send_lifecycle'),
            'admission must complete before the transport call')

    def test_probe_passes_exact_snapshot_token_to_send(self):
        probe = self._probe_src()
        self.assertIn("snapshot['token']", probe)
        send_src = inspect.getsource(
            client_module.ShopifyConnectorApiClient._send_lifecycle)
        self.assertIn('self._send(store, body, token)', send_src)

    def test_post_network_revalidation_remains(self):
        probe = self._probe_src()
        self.assertIn('_lifecycle_probe_superseded(snapshot)', probe)
        reval = inspect.getsource(
            store_module.ShopifyConnectorStore._lifecycle_probe_superseded)
        self.assertIn('_lock_store_for_lifecycle', reval)
        self.assertIn('_lifecycle_credential_version', reval)
        self.assertIn("snapshot['generation']", reval)
        self.assertIn("snapshot['token']", reval)

    def test_admission_refusal_before_send_is_superseded(self):
        # A matrix refusal under the lock (disconnect won before the FOR SHARE)
        # is caught and audited as superseded, with no network issued.
        probe = self._probe_src()
        self.assertIn('except UserError:', probe)
        self.assertIn('_audit_probe_superseded(job)', probe)


class TestSourceGuardDetectors(TransactionCase):
    """Detector self-tests (control-room review 4692156428) -- guard the guards.

    Prove each reusable AST source-guard helper both (a) FIRES on real unsafe
    EXECUTABLE code and (b) IGNORES a docstring-only mention of the same token.
    This makes the correction non-circular: it does not rely only on the current
    safe production source, so a future weakening (reverting to a raw
    `assertNotIn` substring scan, or a detector that could never fail) is caught
    here. Pure AST -- no database access."""

    @staticmethod
    def _fn(src):
        return ast.parse(textwrap.dedent(src)).body[0]

    def test_sudo_detector_fires_on_real_call_and_ignores_docstring(self):
        # Guard A (test_credential_service): a real `.sudo()` call is detected;
        # a docstring that says "no sudo()" is not.
        unsafe = self._fn(
            "def bad(self, store):\n"
            "    'plain docstring, no forbidden prose'\n"
            "    return self.sudo().search([('store_id', '=', store.id)])\n"
        )
        safe = self._fn(
            "def ok(self, store):\n"
            "    'Runs with no sudo() -- the ACL stays live (prose only).'\n"
            "    return self.search([('store_id', '=', store.id)])\n"
        )
        self.assertIn('sudo', guard_called_names(unsafe))
        self.assertNotIn('sudo', guard_called_names(safe))

    def test_skip_locked_detector_fires_on_real_sql_and_ignores_docstring(self):
        # Guard B: SKIP LOCKED in real executable SQL is detected; a docstring
        # that explains it does *not* use SKIP LOCKED is not.
        unsafe = self._fn(
            "def bad(self):\n"
            "    'plain docstring'\n"
            "    self.env.cr.execute('SELECT id FROM t WHERE id=%s "
            "FOR UPDATE SKIP LOCKED', (1,))\n"
        )
        safe = self._fn(
            "def ok(self):\n"
            "    'Unlike FOR UPDATE SKIP LOCKED, this blocks (prose only).'\n"
            "    self.env.cr.execute('SELECT id FROM t WHERE id=%s "
            "FOR NO KEY UPDATE', (1,))\n"
        )
        self.assertIn('SKIP LOCKED', guard_execute_sql(unsafe))
        self.assertNotIn('SKIP LOCKED', guard_execute_sql(safe))
        self.assertIn('FOR NO KEY UPDATE', guard_execute_sql(safe))

    def test_clear_detector_fires_on_real_call_and_ignores_docstring(self):
        # Guard C: a real public `action_clear_token()` call is detected; a
        # finalizer docstring that says "never the public action_clear_token"
        # is not (and the private primitive is still required).
        unsafe = self._fn(
            "def bad(self):\n"
            "    'finalizer'\n"
            "    self.env['x'].action_clear_token(self)\n"
        )
        safe = self._fn(
            "def ok(self):\n"
            "    'Clears via the private primitive, never the public "
            "action_clear_token.'\n"
            "    self.env['x']._clear_token_under_store_lock(self)\n"
        )
        self.assertIn('action_clear_token', guard_called_names(unsafe))
        self.assertNotIn('action_clear_token', guard_called_names(safe))
        self.assertIn(
            '_clear_token_under_store_lock', guard_called_names(safe))

    def test_lease_detector_fires_on_real_create_and_ignores_docstring(self):
        # Guard D: a real call-lease model create() (model lookup + `lease_key`
        # identifier + create call) is detected; a docstring that says "no
        # call.lease is created" is not.
        unsafe = self._fn(
            "def bad(self, side_env):\n"
            "    'admission'\n"
            "    lease_key = uuid.uuid4().hex\n"
            "    side_env['shopify.connector.call.lease'].create("
            "{'lease_key': lease_key})\n"
        )
        safe = self._fn(
            "def ok(self, token):\n"
            "    'Snapshot only; no call.lease is created and no lease_key "
            "exists.'\n"
            "    return {'token': token}\n"
        )
        self.assertIn(
            'shopify.connector.call.lease', guard_str_constants(unsafe))
        self.assertIn('lease_key', guard_identifiers(unsafe))
        self.assertIn('create', guard_called_names(unsafe))
        self.assertNotIn(
            'shopify.connector.call.lease', guard_str_constants(safe))
        self.assertNotIn('lease_key', guard_identifiers(safe))
        self.assertNotIn('create', guard_called_names(safe))

    def test_limit_kwarg_detector_requires_a_real_call(self):
        # Guard C helper: try_lock_for_update(limit=1) must be a real call with
        # the literal kwarg; a docstring mention alone does not satisfy it.
        real = self._fn(
            "def q(self):\n"
            "    'doc'\n"
            "    return self.search([]).try_lock_for_update(limit=1)\n"
        )
        prose_only = self._fn(
            "def q(self):\n"
            "    'uses try_lock_for_update(limit=1) -- prose only'\n"
            "    return self.search([]).try_lock_for_update()\n"
        )
        self.assertTrue(guard_has_call_with_const_kwarg(
            real, 'try_lock_for_update', 'limit', 1))
        self.assertFalse(guard_has_call_with_const_kwarg(
            prose_only, 'try_lock_for_update', 'limit', 1))


class _GenuineRaceHelpers:
    """Shared GENUINE independent-connection helpers (mixin; mirrors
    `TestGenuineRealAdmission` / `TestCredentialReplacementRaceGenuine`): real
    pooled `db_connect` connections, bounded (statement_timeout + lock_timeout),
    with distinct backend PIDs. Raw SQL is used ONLY to commit fixtures, OBSERVE
    committed state, and clean up -- never to create the row under test."""

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    def _open_bounded(self, dbname, read_committed=False, lock_timeout_ms=None):
        """Open a genuine pooled cursor with BOTH transaction-local PostgreSQL
        limits. `read_committed=True` (first statement of the transaction) lets a
        single-shot genuine test observe the post-network FOR NO KEY UPDATE
        revalidation against a concurrently-committed disconnect WITHOUT the
        production request-level serialization-failure retry (production runs
        REPEATABLE READ + that retry; both converge on discarding the stale probe
        result). `lock_timeout_ms` overrides the default lock timeout for the
        lock-attribution proof."""
        cr = db_connect(dbname).cursor()
        try:
            if read_committed:
                cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            lt = self.LOCK_TIMEOUT_MS if lock_timeout_ms is None else lock_timeout_ms
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(lt)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _backend_pid(self, cr):
        cr.execute("SELECT pg_backend_pid()")
        return cr.fetchone()[0]

    def _real_registry_cursor(self, dbname):
        """registry.cursor() replacement handing out bounded real pooled cursors,
        so the production side transactions (`_admit`/`_admit_lifecycle`/
        `_release_lease`) are genuinely independent and time-bounded."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _recording_registry_cursor(self, dbname, pids, lock_timeout_ms=None):
        """As `_real_registry_cursor`, but records each handed-out cursor's backend
        PID so the production side transaction's backend is observably distinct."""
        def factory(*args, **kwargs):
            cr = self._open_bounded(dbname, lock_timeout_ms=lock_timeout_ms)
            pids.append(self._backend_pid(cr))
            return cr
        return factory

    def _sanitize(self, exc, phase):
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _drain(self, q):
        findings = []
        while True:
            try:
                findings.append(q.get_nowait())
            except queue.Empty:
                break
        return findings

    def _assert_workers_dead(self, threads):
        alive = sum(1 for t in threads if t is not None and t.is_alive())
        self.assertEqual(
            alive, 0, 'worker thread still alive at the cleanup boundary')

    def _commit_connected_fixture(self, dbname, with_job=False):
        """Create+commit a connected store, its credential, and (optionally) one
        matching business job on an independent bounded connection. Returns
        `(store_id, shop_domain, job_id)`."""
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            shop_domain = 'genuine-lifecycle-%s.myshopify.com' % uuid.uuid4().hex
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Lifecycle Race Store',
                'shop_domain': shop_domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            job_id = None
            if with_job:
                job = env['shopify.connector.job.enqueue'].enqueue(
                    store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash=uuid.uuid4().hex,
                )
                job_id = job.id
            store_id = store.id
            setup.commit()
            return store_id, shop_domain, job_id
        finally:
            setup.close()

    def _observe_store(self, dbname, store_id):
        """(state, connection_generation, last_test_connection_result,
        credential_last_verified_at, credential_present) from a fresh connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, connection_generation, "
                "last_test_connection_result, credential_last_verified_at, "
                "credential_present FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _observe_credential_token(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT access_token FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _observe_latest_probe_job(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, cancel_reason FROM shopify_connector_job "
                "WHERE store_id = %s AND job_type = 'core_test_connection' "
                "ORDER BY id DESC LIMIT 1", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _lease_count(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            n = obs.fetchone()[0]
            obs.rollback()
            return n
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id):
        """Durable, bounded, fail-loud teardown + fresh zero-residue check
        (job logs before jobs for the FK restrict)."""
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            # Disconnect requests + quiescing controller passes schedule cron
            # triggers (action_disconnect / delayed re-poll); job enqueue may
            # schedule the drain cron. Remove both so no cron-trigger residue
            # survives (matching TestDisconnectControllerSelectionGenuine).
            cr.execute(
                "DELETE FROM ir_cron_trigger WHERE cron_id IN "
                "(SELECT res_id FROM ir_model_data WHERE module = "
                "'shopify_connector_core' AND name IN "
                "('ir_cron_shopify_connector_disconnect_quiesce', "
                "'ir_cron_shopify_connector_job_dispatch_drain'))")
            cr.execute(
                "DELETE FROM shopify_connector_job_log WHERE job_id IN "
                "(SELECT id FROM shopify_connector_job WHERE store_id = %s)",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_job WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        self._assert_zero_residue(dbname, store_id)

    def _assert_zero_residue(self, dbname, store_id):
        v = self._open_bounded(dbname)
        try:
            for table, col, label in (
                ('shopify_connector_call_lease', 'store_id', 'lease'),
                ('shopify_connector_store', 'id', 'store'),
                ('shopify_connector_store_credential', 'store_id', 'credential'),
                ('shopify_connector_job', 'store_id', 'job'),
            ):
                v.execute(
                    "SELECT count(*) FROM %s WHERE %s = %%s" % (table, col),
                    (store_id,))
                self.assertEqual(
                    v.fetchone()[0], 0, '%s residue after cleanup' % label)
            v.rollback()
        finally:
            v.close()


@tagged('post_install', '-at_install')
class TestLifecycleAdmissionRaceGenuine(_GenuineRaceHelpers, TransactionCase):
    """CORE-R2 review 4691182306 #1/#2 -- GENUINE independent-transaction proof
    that the atomic lifecycle admission (`_admit_lifecycle`, a store-row FOR SHARE
    side transaction) linearizes a connection probe against `action_disconnect`
    across DISTINCT PostgreSQL backends. Proves both orders (admission-first,
    disconnect-first), that a disconnect-first order issues ZERO transport calls,
    that an admission-first order finishes with its exact captured OLD token and is
    then discarded as superseded with NO mirror written, that the admission takes a
    store-row lock conflicting with the lifecycle FOR NO KEY UPDATE, and a final
    THREADED case proving genuine simultaneity via the accepted Registry._lock
    bounded-window pattern.

    The production side transaction's own `registry.cursor()` is made genuinely
    independent (real bounded pooled cursor, distinct backend, committed) by
    patching the registry cursor factory for the bounded window (mirroring
    `TestGenuineRealAdmission`). Deterministic orderings are established by
    controlling which independent transaction commits first; the threaded case
    adds real wall-clock concurrency. Raw SQL only observes/cleans up. The full
    two-server production proof (T-19) remains a deferred Odoo.sh item (SRR-09)."""

    # A. Disconnect wins FIRST -> the admission FOR SHARE (fresh, distinct backend)
    # reads the committed `disconnecting` row the worker's stale snapshot did not
    # see, refuses UNDER the lock, and issues ZERO transport calls.
    def test_disconnect_first_probe_superseded_zero_transport(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        send_calls = []
        try:
            store_id, _domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                worker_pid = self._backend_pid(worker)
                store = wenv['shopify.connector.store'].browse(store_id)
                self.assertEqual(store.state, 'connected')   # fix stale snapshot
                Client = wenv['shopify.connector.api.client']

                disc = self._open_bounded(dbname)
                try:
                    denv = api.Environment(disc, SUPERUSER_ID, {})
                    pids.append(self._backend_pid(disc))
                    denv['shopify.connector.store'].browse(
                        store_id).action_disconnect()
                    disc.commit()
                finally:
                    disc.close()

                def spy_send(client_self, s, body, token=None):
                    send_calls.append(1)
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    with patch.object(type(Client), '_send', spy_send):
                        store.action_test_connection()
                # The pre-check passed on the worker's stale 'connected' snapshot;
                # the admission side cursor's FOR SHARE read committed
                # 'disconnecting' (distinct backend) and refused -> superseded,
                # no transport.
                job = wenv['shopify.connector.job'].search([
                    ('store_id', '=', store_id),
                    ('job_type', '=', 'core_test_connection'),
                ], order='id desc', limit=1)
                self.assertEqual(job.state, 'cancelled')
                self.assertIn('superseded', job.cancel_reason)
                worker.rollback()
            finally:
                worker.close()
            self.assertEqual(send_calls, [])                        # ZERO transport
            self.assertGreaterEqual(len(set(pids + [worker_pid])), 2)  # distinct PIDs
            self.assertEqual(self._lease_count(dbname, store_id), 0)   # no lease
        finally:
            self._cleanup(dbname, store_id)

    # B. Admission wins FIRST -> it captures the OLD token/generation; a disconnect
    # committed on a distinct backend during the call is caught by the post-network
    # revalidation: the probe finishes with its captured OLD token but the stale
    # result is discarded (superseded) with NO mirror written.
    def test_admission_first_uses_old_token_then_disconnect_supersedes(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        captured = {}
        try:
            store_id, shop_domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname, read_committed=True)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                worker_pid = self._backend_pid(worker)
                store = wenv['shopify.connector.store'].browse(store_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, body, token=None):
                    # Admission already committed its FOR SHARE snapshot (old gen,
                    # old token). A REAL one-way disconnect now wins on an
                    # INDEPENDENT connection; it does not block (the admission
                    # FOR SHARE released at commit) and bumps the generation.
                    captured['token'] = token
                    disc = self._open_bounded(dbname)
                    try:
                        denv = api.Environment(disc, SUPERUSER_ID, {})
                        pids.append(self._backend_pid(disc))
                        denv['shopify.connector.store'].browse(
                            store_id).action_disconnect()
                        disc.commit()
                    finally:
                        disc.close()
                    return FakeResponse(
                        200, json_body=_success_body(domain=shop_domain))

                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    with patch.object(type(Client), '_send', racing_send):
                        store.action_test_connection()
                # The admitted probe finished with EXACTLY its captured OLD token.
                self.assertEqual(captured['token'], DUMMY_TOKEN)
                # The post-network revalidation discarded the stale result.
                job = wenv['shopify.connector.job'].search([
                    ('store_id', '=', store_id),
                    ('job_type', '=', 'core_test_connection'),
                ], order='id desc', limit=1)
                self.assertEqual(job.state, 'cancelled')
                self.assertIn('superseded', job.cancel_reason)
                store.invalidate_recordset()
                self.assertEqual(store.state, 'disconnecting')  # disconnect won
                self.assertNotEqual(store.last_test_connection_result, 'pass')
                self.assertFalse(store.credential_last_verified_at)  # no mirror
                worker.rollback()
            finally:
                worker.close()
            self.assertGreaterEqual(len(set(pids + [worker_pid])), 2)  # distinct PIDs
            # Credential value intact (disconnect does not clear until the
            # controller finalizes); the superseded probe wrote no credential state.
            self.assertEqual(
                self._observe_credential_token(dbname, store_id), DUMMY_TOKEN)
        finally:
            self._cleanup(dbname, store_id)

    # Store-row lock attribution: the admission FOR SHARE conflicts with a held
    # lifecycle FOR NO KEY UPDATE (distinct backend) -> it blocks and hits its
    # bounded lock_timeout; once the holder releases, the admission succeeds.
    def test_admission_for_share_conflicts_with_lifecycle_update_lock(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        try:
            store_id, _domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            holder = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                Client = wenv['shopify.connector.api.client']
                holder_pid = self._backend_pid(holder)
                # An independent connection holds the conflicting lifecycle update
                # lock (FOR NO KEY UPDATE) on the store row, uncommitted.
                holder.execute(
                    "SELECT id FROM shopify_connector_store WHERE id = %s "
                    "FOR NO KEY UPDATE", (store_id,))
                # The admission FOR SHARE must BLOCK on that lock and hit its
                # bounded lock_timeout -> raises (proving it takes a conflicting
                # store-row lock, on a distinct backend).
                with patch.object(
                    self.registry, 'cursor',
                    self._recording_registry_cursor(
                        dbname, pids, lock_timeout_ms=500)):
                    with self.assertRaises(psycopg2.OperationalError):
                        Client._admit_lifecycle(store, 'test_connection')
                # Release the holder -> the admission now succeeds (it was the lock).
                holder.rollback()
                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    snapshot = Client._admit_lifecycle(store, 'test_connection')
                self.assertEqual(snapshot['token'], DUMMY_TOKEN)
                worker.rollback()
            finally:
                holder.rollback()
                holder.close()
                worker.close()
            self.assertGreaterEqual(len(set(pids + [holder_pid])), 2)  # distinct PIDs
        finally:
            self._cleanup(dbname, store_id)

    # Genuine SIMULTANEITY (threaded): a worker admits and parks at the transport
    # seam on one backend while a disconnect commits on another; the worker's
    # post-network revalidation then supersedes the stale result. Uses the accepted
    # Registry._lock bounded-window pattern; no cursor/Environment is passed
    # between threads.
    def test_genuine_concurrent_admission_superseded_by_disconnect(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        parked = threading.Semaphore(0)
        gate = threading.Event()
        diagnostics = queue.Queue()
        results = queue.Queue()
        worker_thread = None
        try:
            store_id, shop_domain, _job = self._commit_connected_fixture(dbname)

            def blocking_send(client_self, s, body, token=None):
                # Admission already committed; signal parked, then wait for the
                # disconnect to commit on the other backend.
                results.put({'token': token})
                parked.release()
                if not gate.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('gate not set within bound')
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def worker():
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname, read_committed=True)
                    worker_pid = self._backend_pid(wcr)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    store = wenv['shopify.connector.store'].browse(store_id)
                    store.action_test_connection()
                    job = wenv['shopify.connector.job'].search([
                        ('store_id', '=', store_id),
                        ('job_type', '=', 'core_test_connection'),
                    ], order='id desc', limit=1)
                    store.invalidate_recordset()
                    results.put({
                        'worker_pid': worker_pid,
                        'job_state': job.state,
                        'cancel': job.cancel_reason or '',
                        'mirror': store.last_test_connection_result or '',
                    })
                except BaseException as exc:
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    if wcr is not None:
                        try:
                            wcr.rollback()
                        except BaseException as exc:
                            diagnostics.put(self._sanitize(exc, 'rollback'))
                        try:
                            wcr.close()
                        except BaseException as exc:
                            diagnostics.put(self._sanitize(exc, 'cursor_close'))

            Client = self.env['shopify.connector.api.client']
            disc_pid = None
            with patch.object(type(self.registry), '_lock', threading.RLock()), \
                 patch.object(self.registry, 'cursor',
                              self._recording_registry_cursor(dbname, pids)):
                with patch.object(type(Client), '_send', blocking_send):
                    worker_thread = threading.Thread(target=worker, daemon=True)
                    worker_thread.start()
                    try:
                        got = parked.acquire(timeout=self.BOUND_SECONDS)
                        if got:
                            # Worker admitted + parked at transport. Disconnect wins
                            # NOW, concurrently, on an independent backend (the
                            # worker holds its own connection open, so this is a
                            # genuinely distinct backend PID).
                            disc = self._open_bounded(dbname)
                            try:
                                denv = api.Environment(disc, SUPERUSER_ID, {})
                                disc_pid = self._backend_pid(disc)
                                pids.append(disc_pid)
                                denv['shopify.connector.store'].browse(
                                    store_id).action_disconnect()
                                disc.commit()
                            finally:
                                disc.close()
                    finally:
                        gate.set()
                        worker_thread.join(timeout=self.BOUND_SECONDS)
                        self._assert_workers_dead((worker_thread,))
            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(got, 'worker did not park at the transport within bound')
            # First queue item is the parked-token; second is the outcome.
            first = results.get_nowait()
            self.assertEqual(first['token'], DUMMY_TOKEN)   # exact captured token
            outcome = results.get_nowait()
            self.assertEqual(outcome['job_state'], 'cancelled')
            self.assertIn('superseded', outcome['cancel'])
            self.assertNotEqual(outcome['mirror'], 'pass')  # no mirror written
            # Genuinely distinct backends: the parked worker (its own held-open
            # connection) and the concurrent disconnect ran on different PIDs.
            self.assertIsNotNone(disc_pid)
            self.assertNotEqual(outcome['worker_pid'], disc_pid)
        finally:
            gate.set()
            if worker_thread is not None:
                worker_thread.join(timeout=self.BOUND_SECONDS)
                self._assert_workers_dead((worker_thread,))
            self._cleanup(dbname, store_id)


@tagged('post_install', '-at_install')
class TestPublicClearAdmissionRaceGenuine(_GenuineRaceHelpers, TransactionCase):
    """CORE-R2 review 4691182306 #2 (§6) -- GENUINE independent-transaction proof
    of the public-clear vs business-admission linearization through the REAL
    `execute_business`/`_admit` boundary and the REAL public `action_clear_token`,
    on distinct PostgreSQL backends. Proves both orders: business admission first
    (the public clear requests two-phase disconnect, the credential is PRESERVED
    while the committed lease is open, and the controller clears it only after the
    lease releases -- one generation bump); public clear first (a later
    old-generation business admission FAILS CLOSED with no lease and no transport,
    and the credential remains until the controller finalizes)."""

    # A. Business admission wins FIRST: the committed lease outlives admission's
    # brief FOR SHARE; a public clear requests two-phase disconnect and clears
    # NOTHING until the controller reaches `completed` (zero holders).
    def test_business_admission_first_defers_clear_until_release(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        captured = {}
        try:
            store_id, shop_domain, job_id = self._commit_connected_fixture(
                dbname, with_job=True)
            initial = self._observe_store(dbname, store_id)
            initial_gen = initial[1]
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, body, token=None):
                    # Business lease already committed (old token captured). A public
                    # clear on the CONNECTED store runs on an INDEPENDENT connection:
                    # it routes through two-phase action_disconnect and clears
                    # NOTHING now.
                    captured['token'] = token
                    clr = self._open_bounded(dbname)
                    try:
                        cenv = api.Environment(clr, SUPERUSER_ID, {})
                        cenv['shopify.connector.store.credential'].action_clear_token(
                            cenv['shopify.connector.store'].browse(store_id))
                        clr.commit()
                    finally:
                        clr.close()
                    # A controller pass with the lease still open -> quiescing,
                    # credential PRESERVED.
                    ctrl = self._open_bounded(dbname)
                    try:
                        ctenv = api.Environment(ctrl, SUPERUSER_ID, {})
                        ctenv['shopify.connector.store']._run_disconnect_quiesce()
                        ctrl.commit()
                    finally:
                        ctrl.close()
                    captured['during'] = self._observe_store(dbname, store_id)
                    captured['token_during'] = self._observe_credential_token(
                        dbname, store_id)
                    captured['lease_during'] = self._lease_count(dbname, store_id)
                    return FakeResponse(
                        200, json_body=_success_body(domain=shop_domain))

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', racing_send):
                        with Client.execute_business(job, store, 'q') as result:
                            self.assertEqual(
                                result['data']['shop']['id'],
                                'gid://shopify/Shop/1')
                worker.rollback()
            finally:
                worker.close()
            # During the call: two-phase requested, credential PRESERVED, lease open.
            self.assertEqual(captured['token'], DUMMY_TOKEN)
            self.assertEqual(captured['during'][0], 'disconnecting')  # state
            self.assertEqual(captured['token_during'], DUMMY_TOKEN)   # NOT cleared
            self.assertEqual(captured['lease_during'], 1)             # lease open
            # After the business call exits (lease released), the controller
            # finalizes and clears the credential -- ONE generation bump total.
            ctrl = self._open_bounded(dbname)
            try:
                ctenv = api.Environment(ctrl, SUPERUSER_ID, {})
                ctenv['shopify.connector.store']._run_disconnect_quiesce()
                ctrl.commit()
            finally:
                ctrl.close()
            final = self._observe_store(dbname, store_id)
            self.assertEqual(final[0], 'disconnected')                # state
            self.assertEqual(final[1], initial_gen + 1)               # ONE bump
            self.assertFalse(
                self._observe_credential_token(dbname, store_id))     # cleared NOW
            self.assertEqual(self._lease_count(dbname, store_id), 0)
        finally:
            self._cleanup(dbname, store_id)

    # B. Public clear wins FIRST: it requests two-phase disconnect (gen +1,
    # credential preserved); a later old-generation business admission FAILS CLOSED
    # (no lease, no transport), and the credential remains until finalization.
    def test_public_clear_first_business_admission_fails_closed(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        captured = {}
        try:
            store_id, _domain, job_id = self._commit_connected_fixture(
                dbname, with_job=True)
            clr = self._open_bounded(dbname)
            try:
                cenv = api.Environment(clr, SUPERUSER_ID, {})
                cenv['shopify.connector.store.credential'].action_clear_token(
                    cenv['shopify.connector.store'].browse(store_id))
                clr.commit()
            finally:
                clr.close()
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def spy_send(client_self, s, b, token=None):
                    captured['token'] = token
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', spy_send):
                        with self.assertRaises(ShopifyQuiescedError):
                            with Client.execute_business(job, store, 'q'):
                                pass
                worker.rollback()
            finally:
                worker.close()
            self.assertNotIn('token', captured)                       # no transport
            self.assertEqual(self._lease_count(dbname, store_id), 0)  # no lease
            row = self._observe_store(dbname, store_id)
            self.assertEqual(row[0], 'disconnecting')                 # clear won
            # Credential remains until the controller finalizes (not cleared by the
            # clear request, not by the refused admission).
            self.assertEqual(
                self._observe_credential_token(dbname, store_id), DUMMY_TOKEN)
        finally:
            self._cleanup(dbname, store_id)


class _RetryLogCapture(logging.Handler):
    """Collects `odoo.service.model` log records so a test can prove the REAL
    `retrying` loop reported a serialization-failure retry (best-effort textual
    corroboration; the definitive cause evidence is the captured pgcode)."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        try:
            self.messages.append(record.getMessage())
        except Exception:
            self.messages.append(
                record.msg if isinstance(record.msg, str) else '')

    def mentions_serialization(self):
        needles = ('serialization', 'serialize', '40001')
        return any(
            any(n in m.lower() for n in needles) for m in self.messages)


@tagged('post_install', '-at_install')
class TestLifecycleServiceRetryGenuine(_GenuineRaceHelpers, TransactionCase):
    """CORE-R2 Section 9 / RT.8 (control-room review 4692156428) -- GENUINE proof
    that a default-REPEATABLE-READ lifecycle probe, driven through the REAL Odoo
    service retry boundary `odoo.service.model.retrying(func, env)`, converges on
    EXACTLY ONE Shopify transport when a concurrent disconnect (committed on an
    INDEPENDENT PostgreSQL backend) forces the post-network store-row
    revalidation to raise a real SQLSTATE 40001 serialization failure.

    This is the missing companion to `TestLifecycleAdmissionRaceGenuine`: that
    class opens its worker cursor READ COMMITTED so it can observe the
    supersession WITHOUT the production retry; this class keeps the NORMAL Odoo
    isolation (REPEATABLE READ) and exercises the genuine retry loop end to end.

    The serialization failure originates from PostgreSQL, never from an injected
    exception: the first attempt establishes its REPEATABLE READ snapshot before
    the disconnect commits, so the post-network `_lifecycle_probe_superseded` ->
    `_lock_store_for_lifecycle` `SELECT ... FOR NO KEY UPDATE` on the row the
    disconnect changed cannot serialize and raises 40001. Odoo's `retrying`
    catches it (SERIALIZATION_FAILURE is in PG_CONCURRENCY_ERRORS_TO_RETRY),
    rolls back, resets the transaction, and re-invokes the callable; the second
    attempt re-browses the store, sees the committed `disconnecting` row, and is
    refused by the frozen matrix BEFORE transport -- so total transport stays
    exactly one and the final safe outcome is the normal lifecycle refusal
    (UserError). No raw serialization error escapes.

    Guarantees (Section 6/9): production isolation is NOT weakened (the main
    cursor runs REPEATABLE READ, asserted), no serialization exception is
    injected, no fake local retry loop is used, no production lock/exception
    handling is touched, and only the retry BACKOFF (jitter/sleep) is patched --
    never the retry decision or exception classification. One main retry
    cursor/env; one INDEPENDENT connection for the disconnect; a patched `_send`
    transport seam; a dummy token only; no live Shopify request. Raw SQL only
    commits the fixture, observes, and cleans up (fresh zero-residue check)."""

    @staticmethod
    @contextlib.contextmanager
    def _no_retry_backoff():
        """Make the REAL `retrying` loop's backoff instantaneous WITHOUT touching
        its retry decision or exception classification: patch only the jitter
        (`random.uniform` -> 0.0) and the wait (`time.sleep` -> no-op), tolerant
        of the module's import form. If a hook is absent the only effect is one
        short real sleep -- still correct."""
        patches = []
        if hasattr(service_model, 'time') and hasattr(
                service_model.time, 'sleep'):
            patches.append(patch.object(
                service_model.time, 'sleep', lambda *a, **k: None))
        elif hasattr(service_model, 'sleep'):
            patches.append(patch.object(
                service_model, 'sleep', lambda *a, **k: None))
        if hasattr(service_model, 'random') and hasattr(
                service_model.random, 'uniform'):
            patches.append(patch.object(
                service_model.random, 'uniform', lambda *a, **k: 0.0))
        elif hasattr(service_model, 'uniform'):
            patches.append(patch.object(
                service_model, 'uniform', lambda *a, **k: 0.0))
        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            yield

    def test_repeatable_read_serialization_retry_issues_one_transport(self):
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []           # one entry per transport invocation (total)
        attempt_send_counts = []   # len(send_tokens) at the START of each attempt
        attempt_pgcodes = []       # OperationalError.pgcode observed per attempt
        disc_info = {}             # backend PID where the disconnect committed
        retry_handler = _RetryLogCapture()
        service_logger = logging.getLogger('odoo.service.model')
        prior_level = service_logger.level
        try:
            store_id, shop_domain, _job = self._commit_connected_fixture(dbname)
            initial_gen = self._observe_store(dbname, store_id)[1]

            # The retry transaction: a GENUINE pooled cursor at the NORMAL Odoo
            # isolation (REPEATABLE READ) -- deliberately NOT read_committed --
            # so the post-network FOR NO KEY UPDATE revalidation raises a real
            # 40001 that the production retry must handle. `_open_bounded`'s first
            # statement establishes this snapshot BEFORE the disconnect commits.
            retry_cr = self._open_bounded(dbname)
            try:
                retry_cr.execute("SHOW transaction_isolation")
                self.assertEqual(
                    retry_cr.fetchone()[0], 'repeatable read',
                    'the main retry cursor must run at the production isolation')
                retry_pid = self._backend_pid(retry_cr)
                retry_env = api.Environment(retry_cr, SUPERUSER_ID, {})
                Client = retry_env['shopify.connector.api.client']

                def racing_send(client_self, s, body, token=None):
                    # Transport seam: the admission FOR SHARE snapshot is already
                    # committed/released. A REAL one-way disconnect now commits on
                    # an INDEPENDENT backend, bumping the generation and moving the
                    # store to `disconnecting`. Committed exactly once (first
                    # attempt); the second attempt is refused before transport.
                    send_tokens.append(token)
                    if 'pid' not in disc_info:
                        disc = self._open_bounded(dbname)
                        try:
                            denv = api.Environment(disc, SUPERUSER_ID, {})
                            disc_info['pid'] = self._backend_pid(disc)
                            denv['shopify.connector.store'].browse(
                                store_id).action_disconnect()
                            disc.commit()
                        finally:
                            disc.close()
                    return FakeResponse(
                        200, json_body=_success_body(domain=shop_domain))

                def func():
                    # Re-browse the store from the retry environment on EVERY
                    # attempt (fresh snapshot each try). Observe -- never
                    # reclassify -- the serialization pgcode, then re-raise so the
                    # REAL `retrying` makes the retry decision.
                    attempt_send_counts.append(len(send_tokens))
                    store = retry_env['shopify.connector.store'].browse(store_id)
                    try:
                        return store.action_test_connection()
                    except psycopg2.OperationalError as exc:
                        attempt_pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

                service_logger.setLevel(logging.DEBUG)
                service_logger.addHandler(retry_handler)
                try:
                    with patch.object(
                            self.registry, 'cursor',
                            self._recording_registry_cursor(dbname, [])), \
                         patch.object(type(Client), '_send', racing_send), \
                         self._no_retry_backoff():
                        # Stale first attempt -> real 40001 -> retrying rolls
                        # back/resets and retries; the reset second attempt is
                        # matrix-refused (disconnecting) BEFORE transport. The
                        # final safe outcome is the normal lifecycle UserError.
                        with self.assertRaises(UserError):
                            retrying(func, retry_env)
                finally:
                    service_logger.removeHandler(retry_handler)
                retry_cr.rollback()
            finally:
                retry_cr.close()

            # ---- retry-boundary assertions ----
            self.assertGreaterEqual(
                len(attempt_send_counts), 2,
                'the callable must be attempted at least twice (a genuine retry)')
            self.assertEqual(
                len(send_tokens), 1,
                'exactly one transport across the attempt + retry')
            self.assertEqual(
                send_tokens[0], DUMMY_TOKEN,
                'the first transport used the captured dummy token')
            # The second attempt issued ZERO transport (matrix-refused before
            # send): its start-of-attempt send count already equals the single
            # total, so it added none.
            self.assertEqual(attempt_send_counts[0], 0)
            self.assertEqual(attempt_send_counts[1], 1)
            # A genuine PostgreSQL serialization failure (SQLSTATE 40001) drove
            # the retry -- captured directly from the OperationalError, and
            # corroborated by the service retry log.
            self.assertIn(
                psycopg2.errorcodes.SERIALIZATION_FAILURE, attempt_pgcodes,
                'the first attempt must fail with a real 40001; saw %s'
                % attempt_pgcodes)
            self.assertTrue(
                retry_handler.messages,
                'the real service retry loop must log its retry')
            self.assertTrue(
                retry_handler.mentions_serialization()
                or psycopg2.errorcodes.SERIALIZATION_FAILURE in attempt_pgcodes,
                'SERIALIZATION_FAILURE must be evidenced as the retry cause '
                '(log=%s; pgcodes=%s)'
                % (retry_handler.messages, attempt_pgcodes))
            # ---- distinct backend for the disconnect ----
            self.assertIn('pid', disc_info)
            self.assertNotEqual(
                disc_info['pid'], retry_pid,
                'the disconnect committed on a distinct backend PID')
            # ---- final committed state (fresh connection) ----
            state, gen, ltc, clv, cred_present = self._observe_store(
                dbname, store_id)
            self.assertEqual(state, 'disconnecting')   # disconnect won, one-way
            self.assertEqual(gen, initial_gen + 1)     # generation bumped once
            self.assertNotEqual(ltc, 'pass')           # no pass result written
            self.assertFalse(ltc)                      # no stale first-attempt fail
            self.assertFalse(clv)  # credential_last_verified_at empty
            self.assertTrue(cred_present)              # credential preserved
            self.assertEqual(
                self._observe_credential_token(dbname, store_id), DUMMY_TOKEN)
            self.assertEqual(self._lease_count(dbname, store_id), 0)  # no lease
        finally:
            service_logger.setLevel(prior_level)
            self._cleanup(dbname, store_id)

    def test_scheduled_run_drain_serialization_retry_refuses_after_disconnect(self):
        """Phase-5 companion proof, corrected for the ownership/replay model
        (control-room review `4699752673`): the SAME genuine 40001-driven conflict
        as ``test_repeatable_read_serialization_retry_...``, but through the REAL
        SCHEDULED job-dispatch entrypoint ``run_drain`` -- now proving the NO-REPLAY
        recovery contract rather than a ``retrying`` re-invocation.

        A representative business handler admits + transports exactly once, then a
        real post-network store-row revalidation (``_lock_store_for_lifecycle``,
        ``FOR NO KEY UPDATE``) raises a genuine SQLSTATE 40001 once a concurrent
        real ``action_disconnect`` has committed on an INDEPENDENT backend. The
        dispatcher NEVER re-issues an ORM write inside the aborted transaction and
        NEVER replays the handler: ``_drain_one`` catches the concurrency failure
        at its per-job outer boundary, rolls back (the lease has already released
        via the ``execute_business`` context exit), resets the environment,
        REACQUIRES the exact job under a real ``FOR UPDATE SKIP LOCKED`` row lock,
        revalidates it as still claimable (its rolled-back ``running`` write is
        gone, so it is ``queued`` again), and routes it ONCE to the bounded
        ``concurrency_race_conflict`` path -> ``retry_waiting`` -- with no second
        transport. Only ``_send`` (the network seam) and the handler registry are
        patched; ``run_drain`` / ``_dispatch_one`` / ``_invoke_handler`` /
        ``_recover_after_concurrency_conflict`` / ``execute_business`` / ``_admit``
        / ``_release_lease`` / ``action_disconnect`` are the REAL production code.
        (Was a ``retrying``-boundary proof asserting the reset RE-INVOCATION was
        gate-refused into ``failed_retryable``; the corrected dispatcher no longer
        replays the handler at all -- runtime correction, review `4699752673`.)
        """
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        disc_info = {}
        try:
            store_id, shop_domain, job_id = self._commit_connected_fixture(
                dbname, with_job=True)
            ClientCls = type(self.env['shopify.connector.api.client'])
            DispatchCls = type(self.env['shopify.connector.job.dispatch'])

            def racing_send(client_self, s, body, token=None):
                # Admission committed the lease + token snapshot; a REAL one-way
                # disconnect now commits ONCE on an INDEPENDENT backend.
                send_tokens.append(token)
                if 'pid' not in disc_info:
                    disc = self._open_bounded(dbname)
                    try:
                        denv = api.Environment(disc, SUPERUSER_ID, {})
                        disc_info['pid'] = self._backend_pid(disc)
                        denv['shopify.connector.store'].browse(
                            store_id).action_disconnect()
                        disc.commit()
                    finally:
                        disc.close()
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def racing_selftest(job):
                # Representative business handler: REAL admission + transport, then
                # a REAL post-network store-row revalidation that raises a genuine
                # 40001 under REPEATABLE READ once the disconnect has committed. The
                # pgcode is observed (never reclassified) then re-raised so the REAL
                # dispatcher recovery -- not this handler -- decides.
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    try:
                        job.store_id._lock_store_for_lifecycle()
                    except psycopg2.OperationalError as exc:
                        pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

            drain_cr = self._open_bounded(dbname)      # production REPEATABLE READ
            try:
                drain_cr.execute("SHOW transaction_isolation")
                self.assertEqual(
                    drain_cr.fetchone()[0], 'repeatable read',
                    'the drain cursor must run at the production isolation')
                drain_pid = self._backend_pid(drain_cr)
                drain_env = api.Environment(drain_cr, SUPERUSER_ID, {})
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)), \
                     patch.object(ClientCls, '_send', racing_send), \
                     patch.object(
                         DispatchCls, '_get_handlers',
                         lambda self: {
                             'core_dispatch_selftest': racing_selftest}):
                    drain_env[
                        'shopify.connector.job.dispatch'].run_drain(1)
            finally:
                drain_cr.close()

            # ---- one-transport + genuine-40001 + no-replay assertions ----
            self.assertEqual(
                len(send_tokens), 1,
                'exactly one transport: the aborted attempt is never replayed')
            self.assertEqual(send_tokens[0], DUMMY_TOKEN)
            self.assertIn(
                psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes,
                'a genuine SQLSTATE 40001 must have aborted the dispatch; saw %s'
                % pgcodes)
            self.assertIn('pid', disc_info)
            self.assertNotEqual(
                disc_info['pid'], drain_pid,
                'the disconnect committed on a distinct backend PID')
            # Aborted attempt released its lease; store superseded; credential
            # retained (the controller finalizes later); job re-locked and routed
            # ONCE to the bounded conflict retry state, never replayed or left raw.
            self.assertEqual(self._lease_count(dbname, store_id), 0)
            state, _gen, _ltc, _clv, cred_present = self._observe_store(
                dbname, store_id)
            self.assertEqual(state, 'disconnecting')
            self.assertTrue(cred_present)
            obs_job = self._open_bounded(dbname)
            try:
                obs_job.execute(
                    "SELECT state FROM shopify_connector_job WHERE id = %s",
                    (job_id,))
                job_state = obs_job.fetchone()[0]
                obs_job.rollback()
            finally:
                obs_job.close()
            self.assertEqual(
                job_state, 'retry_waiting',
                'the superseded job must be re-locked and routed once to the '
                'bounded conflict retry state, never replayed or left raw; saw %s'
                % job_state)
        finally:
            self._cleanup(dbname, store_id)


@tagged('post_install', '-at_install')
class TestDrainOwnershipReplayGenuine(_GenuineRaceHelpers, TransactionCase):
    """Runtime correction (control-room review `4699752673`) -- GENUINE
    independent-connection proofs of the corrected job-dispatch ownership/replay
    model in ``shopify_connector_job_dispatch.py``.

    The dispatcher no longer wraps the handler in ``odoo.service.model.retrying``
    (which would auto-replay a complete handler after a Shopify transport and
    re-drive a job by a bare id without reacquiring the row-lock claim the
    rollback released). Instead ``_drain_one`` runs the handler once under a held
    ``FOR UPDATE SKIP LOCKED`` claim and commits per job; a genuine PostgreSQL
    concurrency failure is recovered by ``_recover_after_concurrency_conflict``:
    roll back, reset, REACQUIRE the exact job under a real row lock, revalidate
    claimability under the lock, and -- only if still safely owned -- route it
    ONCE to the bounded ``concurrency_race_conflict`` path, never replaying the
    handler.

    All connections are genuine pooled ``db_connect`` cursors (REPEATABLE READ,
    bounded by statement/lock timeouts, distinct backend PIDs); every 40001 is a
    REAL PostgreSQL serialization failure (never an injected exception), driven
    by a concurrently-committed benign store-row UPDATE (``write_date`` only --
    the store stays ``connected`` and admission still passes) conflicting with
    the real ``_lock_store_for_lifecycle`` ``FOR NO KEY UPDATE``. Only ``_send``
    and the handler registry (plus, for the reclaim-window proofs, a park barrier
    wrapping the REAL ``_route_failure`` / ``try_lock_for_update`` -- never their
    logic) are patched; the whole claim/dispatch/recovery path is REAL production
    code. Raw SQL only commits fixtures, induces the benign conflict, observes,
    and cleans up (fresh zero-residue check)."""

    # ------------------------------------------------------------------
    # Fixtures / observers (genuine, bounded, independent connections)
    # ------------------------------------------------------------------

    def _commit_store_with_jobs(
        self, dbname, n_jobs=1, retry_counts=None, initial_states=None,
    ):
        """Commit a connected store + credential + claimable business jobs.

        The normal enqueue service creates every row in queued. A controlled
        superuser setup then prepares only an explicitly requested due
        retry_waiting state and/or retry count through the real job model;
        fixtures never rely on an illegal production transition. Returns
        (store_id, shop_domain, [job_id, ...]) with ids in claim order.
        """
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            shop_domain = 'genuine-drain-%s.myshopify.com' % uuid.uuid4().hex
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Drain Ownership Store',
                'shop_domain': shop_domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            states = initial_states or ['queued'] * n_jobs
            counts = retry_counts or [0] * n_jobs
            self.assertEqual(len(states), n_jobs)
            self.assertEqual(len(counts), n_jobs)
            job_ids = []
            for index in range(n_jobs):
                job = env['shopify.connector.job.enqueue'].enqueue(
                    store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash=uuid.uuid4().hex,
                )
                values = {'retry_count': counts[index]}
                if states[index] == 'retry_waiting':
                    values.update({
                        'state': 'retry_waiting',
                        'next_retry_at': (
                            fields.Datetime.now() - timedelta(seconds=1)
                        ),
                    })
                else:
                    self.assertEqual(states[index], 'queued')
                job.sudo().write(values)
                job_ids.append(job.id)
            store_id = store.id
            setup.commit()
            return store_id, shop_domain, job_ids
        finally:
            setup.close()

    def _commit_benign_store_bump(self, dbname, store_id, info=None):
        """Commit a benign store-row UPDATE (``write_date`` only -- ``state`` and
        ``connection_generation`` untouched, so the store stays ``connected`` and
        admission still passes) on an INDEPENDENT backend. Under REPEATABLE READ
        this makes the drain's later ``_lock_store_for_lifecycle`` ``FOR NO KEY
        UPDATE`` raise a genuine 40001. Records the committing backend PID."""
        c = self._open_bounded(dbname)
        try:
            pid = self._backend_pid(c)
            c.execute(
                "UPDATE shopify_connector_store SET write_date = now() "
                "WHERE id = %s", (store_id,))
            c.commit()
            if info is not None:
                info['pid'] = pid
            return pid
        finally:
            c.close()

    def _observe_job(self, dbname, job_id):
        """(state, retry_count) for a job, read + rolled back on a fresh
        connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, retry_count FROM shopify_connector_job "
                "WHERE id = %s", (job_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _assert_direct_recovery_routes(
        self, expected_state, retry_count=0, replay_policies=None,
    ):
        """Recover from both committed claimable states without replay."""
        dbname = self.env.cr.dbname
        store_id = None
        relocked = []
        handler_calls = []
        initial_states = ['queued', 'retry_waiting']
        try:
            store_id, _shop_domain, job_ids = self._commit_store_with_jobs(
                dbname,
                n_jobs=2,
                retry_counts=[retry_count, retry_count],
                initial_states=initial_states,
            )
            recovery_cr = self._open_bounded(dbname)
            try:
                recovery_env = api.Environment(
                    recovery_cr, SUPERUSER_ID, {},
                )
                DispatchCls = type(
                    recovery_env['shopify.connector.job.dispatch']
                )
                JobCls = type(recovery_env['shopify.connector.job'])
                real_try_lock = JobCls.try_lock_for_update

                def recording_try_lock(records, *args, **kwargs):
                    relocked.append(tuple(records.ids))
                    return real_try_lock(records, *args, **kwargs)

                def recording_handler(job):
                    handler_calls.append(job.id)

                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(
                        JobCls, 'try_lock_for_update', recording_try_lock,
                    ))
                    stack.enter_context(patch.object(
                        DispatchCls, '_get_handlers',
                        lambda self: {
                            'core_dispatch_selftest': recording_handler,
                        },
                    ))
                    if replay_policies is not None:
                        stack.enter_context(patch.object(
                            DispatchCls, '_get_replay_policies',
                            lambda self: dict(replay_policies),
                        ))
                    dispatch = recovery_env[
                        'shopify.connector.job.dispatch'
                    ]
                    for job_id in job_ids:
                        dispatch._recover_after_concurrency_conflict(job_id)
            finally:
                recovery_cr.close()

            self.assertEqual(
                relocked, [(job_ids[0],), (job_ids[1],)],
                'recovery must re-lock each exact job once before routing',
            )
            self.assertEqual(
                handler_calls, [],
                'concurrency recovery must never replay the handler',
            )
            for job_id in job_ids:
                state, observed_retry_count = self._observe_job(
                    dbname, job_id,
                )
                self.assertEqual(state, expected_state)
                if expected_state in ('retry_waiting', 'failed_final'):
                    self.assertEqual(
                        observed_retry_count, retry_count + 1,
                    )
                else:
                    self.assertEqual(observed_retry_count, retry_count)
        finally:
            self._cleanup(dbname, store_id)

    def test_recovery_queued_and_due_retry_safe_budget_routes_retry_waiting(self):
        self._assert_direct_recovery_routes('retry_waiting')

    def test_recovery_queued_and_due_retry_exhaustion_routes_failed_final(self):
        self._assert_direct_recovery_routes(
            'failed_final', retry_count=RETRY_MAX_ATTEMPTS,
        )

    def test_recovery_queued_and_due_retry_remote_effect_routes_manual_review(self):
        self._assert_direct_recovery_routes(
            'blocked_manual_review',
            replay_policies={
                'core_dispatch_selftest': 'remote_effect_not_replay_safe',
            },
        )

    def test_recovery_queued_and_due_retry_undeclared_routes_manual_review(self):
        self._assert_direct_recovery_routes(
            'blocked_manual_review', replay_policies={},
        )

    # ------------------------------------------------------------------
    # Test B -- still-connected post-transport serialization failure
    # ------------------------------------------------------------------

    def test_b_still_connected_post_transport_serialization_routes_once(self):
        """Test B -- a genuine post-transport 40001 while the store stays
        CONNECTED (no disconnect). Proves exactly one transport, the complete
        handler is NOT automatically replayed, the job is routed once through the
        accepted ``concurrency_race_conflict`` state contract under a reacquired
        lock, and no raw SerializationFailure / InFailedSqlTransaction becomes the
        final result. This is the companion the disconnect-only proof lacked."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        conflict = {}
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(dbname)
            job_id = job_ids[0]
            ClientCls = type(self.env['shopify.connector.api.client'])
            DispatchCls = type(self.env['shopify.connector.job.dispatch'])

            def ok_send(client_self, s, body, token=None):
                # One transport; then commit a benign store bump on an independent
                # backend so the post-network revalidation serializes-fails while
                # the store REMAINS connected.
                send_tokens.append(token)
                if 'pid' not in conflict:
                    self._commit_benign_store_bump(dbname, store_id, conflict)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def conflicting_selftest(job):
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    try:
                        job.store_id._lock_store_for_lifecycle()
                    except psycopg2.OperationalError as exc:
                        pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

            drain_cr = self._open_bounded(dbname)
            try:
                drain_cr.execute("SHOW transaction_isolation")
                self.assertEqual(drain_cr.fetchone()[0], 'repeatable read')
                drain_pid = self._backend_pid(drain_cr)
                drain_env = api.Environment(drain_cr, SUPERUSER_ID, {})
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)), \
                     patch.object(ClientCls, '_send', ok_send), \
                     patch.object(
                         DispatchCls, '_get_handlers',
                         lambda self: {
                             'core_dispatch_selftest': conflicting_selftest}):
                    drain_env['shopify.connector.job.dispatch'].run_drain(1)
            finally:
                drain_cr.close()

            self.assertEqual(
                len(send_tokens), 1,
                'exactly one transport; the handler is not replayed')
            self.assertEqual(send_tokens[0], DUMMY_TOKEN)
            self.assertIn(
                psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes,
                'a genuine SQLSTATE 40001 must have aborted the dispatch; saw %s'
                % pgcodes)
            self.assertIn('pid', conflict)
            self.assertNotEqual(
                conflict['pid'], drain_pid,
                'the conflicting bump committed on a distinct backend')
            # The store stayed connected the whole time (no disconnect involved).
            state, _gen, _ltc, _clv, cred_present = self._observe_store(
                dbname, store_id)
            self.assertEqual(
                state, 'connected', 'Test B keeps the store connected throughout')
            self.assertTrue(cred_present)
            # Routed ONCE to the bounded conflict retry state -- not a raw error,
            # not a replay -- under the reacquired lock.
            job_state, retry_count = self._observe_job(dbname, job_id)
            self.assertEqual(
                job_state, 'retry_waiting',
                'the still-connected conflicted job must route once to the '
                'accepted concurrency-conflict retry state; saw %s' % job_state)
            self.assertEqual(
                retry_count, 1, 'exactly one bounded-retry increment recorded')
            self.assertEqual(
                self._lease_count(dbname, store_id), 0,
                'the aborted attempt released its lease')
        finally:
            self._cleanup(dbname, store_id)

    # ------------------------------------------------------------------
    # DEC-031 Layer 1 (AR-048) -- fail-closed replay-policy recovery routing.
    # ------------------------------------------------------------------

    def test_conservative_replay_policy_routes_to_blocked_manual_review_not_retry(
            self):
        """The SAME genuine post-transport 40001 as Test B, but with a
        SYNTHETIC replay-policy override forcing `core_dispatch_selftest` to
        the conservative `remote_effect_not_replay_safe` class (never its
        real, accepted `local_only` policy -- this proves the routing
        branch only, not a real production classification change, and
        introduces no Shopify-mutation handler). `_recover_after_
        concurrency_conflict` still rolls back, resets, REACQUIRES the exact
        job under a real row lock, and revalidates claimability exactly as
        Test B does; but because the declared policy is not one of the
        read-safe retry classes, it routes to `blocked_manual_review` /
        `duplicate_risk` instead of the bounded `concurrency_race_conflict`
        auto-retry path -- no automatic retry, never `retry_waiting`, and
        the handler is never invoked a second time (exactly one transport,
        same as Test B)."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        conflict = {}
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(dbname)
            job_id = job_ids[0]
            ClientCls = type(self.env['shopify.connector.api.client'])
            DispatchCls = type(self.env['shopify.connector.job.dispatch'])

            def ok_send(client_self, s, body, token=None):
                send_tokens.append(token)
                if 'pid' not in conflict:
                    self._commit_benign_store_bump(dbname, store_id, conflict)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def conflicting_selftest(job):
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    try:
                        job.store_id._lock_store_for_lifecycle()
                    except psycopg2.OperationalError as exc:
                        pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

            def conservative_only_policy(self):
                # Synthetic override only -- never the real accepted core
                # mapping (`local_only`) -- to exercise the conservative
                # recovery branch without a real Shopify-mutation handler.
                return {
                    'core_dispatch_selftest': 'remote_effect_not_replay_safe',
                }

            drain_cr = self._open_bounded(dbname)
            try:
                drain_cr.execute("SHOW transaction_isolation")
                self.assertEqual(drain_cr.fetchone()[0], 'repeatable read')
                drain_pid = self._backend_pid(drain_cr)
                drain_env = api.Environment(drain_cr, SUPERUSER_ID, {})
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)), \
                     patch.object(ClientCls, '_send', ok_send), \
                     patch.object(
                         DispatchCls, '_get_handlers',
                         lambda self: {
                             'core_dispatch_selftest': conflicting_selftest}), \
                     patch.object(
                         DispatchCls, '_get_replay_policies',
                         conservative_only_policy):
                    drain_env['shopify.connector.job.dispatch'].run_drain(1)
            finally:
                drain_cr.close()

            self.assertEqual(
                len(send_tokens), 1,
                'exactly one transport; the handler is never replayed, even '
                'on the conservative recovery path')
            self.assertEqual(send_tokens[0], DUMMY_TOKEN)
            self.assertIn(
                psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes,
                'a genuine SQLSTATE 40001 must have aborted the dispatch; saw %s'
                % pgcodes)
            self.assertIn('pid', conflict)
            self.assertNotEqual(
                conflict['pid'], drain_pid,
                'the conflicting bump committed on a distinct backend')
            state, _gen, _ltc, _clv, cred_present = self._observe_store(
                dbname, store_id)
            self.assertEqual(
                state, 'connected',
                'this scenario keeps the store connected throughout')
            self.assertTrue(cred_present)
            obs = self._open_bounded(dbname)
            try:
                obs.execute(
                    "SELECT state, error_class, manual_review_subreason "
                    "FROM shopify_connector_job WHERE id = %s", (job_id,))
                job_state, error_class, manual_review_subreason = obs.fetchone()
                obs.rollback()
            finally:
                obs.close()
            self.assertEqual(
                job_state, 'blocked_manual_review',
                'a policy not declared replay-safe must never reach the '
                'auto-retry concurrency_race_conflict path; saw %s'
                % job_state)
            self.assertEqual(error_class, 'duplicate_risk')
            self.assertEqual(manual_review_subreason, 'duplicate_risk')
            self.assertEqual(
                self._lease_count(dbname, store_id), 0,
                'the aborted attempt released its lease')
        finally:
            self._cleanup(dbname, store_id)

    # ------------------------------------------------------------------
    # Test A -- post-rollback reclaim race (SKIP-LOCKED mutual exclusion)
    # ------------------------------------------------------------------

    def test_a_rollback_reclaim_race_one_owner_one_transport(self):
        """Test A -- the post-rollback reclaim race. Worker A transports once,
        hits a genuine 40001, rolls back (losing its claim), and reacquires the
        exact job under a real ``FOR UPDATE`` lock; while A holds that reacquired
        lock, Worker B's genuine ``_claim_for_dispatch`` is SKIP-LOCKED out and
        obtains NOTHING -- no dispatch, no state transition. Exactly one worker
        owns the post-rollback claim; total transport stays exactly one; the job
        reaches one deterministic safe state; no lease / partial data remains."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        conflict = {}
        result = {}
        diagnostics = queue.Queue()
        a_holds_lock = threading.Semaphore(0)
        b_done = threading.Event()
        registry_cls = type(self.registry)
        ClientCls = type(self.env['shopify.connector.api.client'])
        DispatchCls = type(self.env['shopify.connector.job.dispatch'])
        real_route_failure = DispatchCls._route_failure
        worker_a = worker_b = None
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(dbname)
            job_id = job_ids[0]

            def ok_send(client_self, s, body, token=None):
                send_tokens.append(token)
                if 'pid' not in conflict:
                    self._commit_benign_store_bump(dbname, store_id, conflict)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def conflicting_selftest(job):
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    try:
                        job.store_id._lock_store_for_lifecycle()
                    except psycopg2.OperationalError as exc:
                        pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

            def parking_route_failure(disp_self, job, error_class, reason,
                                      technical_detail=False):
                # Worker A reaches this ONLY from its recovery, AFTER it has
                # reacquired the exact job under FOR UPDATE. Park here (holding
                # that lock) so Worker B genuinely races the claim while A owns it,
                # then delegate to the REAL routing unchanged.
                if getattr(threading.current_thread(), 'is_worker_a', False):
                    a_holds_lock.release()
                    if not b_done.wait(timeout=self.BOUND_SECONDS):
                        raise AssertionError('b_done not set within bound')
                return real_route_failure(
                    disp_self, job, error_class, reason, technical_detail)

            def worker_a_fn():
                acr = None
                try:
                    th = threading.current_thread()
                    th.is_worker_a = True
                    th.dbname = dbname
                    acr = self._open_bounded(dbname)
                    result['a_pid'] = self._backend_pid(acr)
                    aenv = api.Environment(acr, SUPERUSER_ID, {})
                    aenv['shopify.connector.job.dispatch'].run_drain(1)
                    acr.commit()
                except BaseException as exc:
                    if acr is not None:
                        try:
                            acr.rollback()
                        except Exception:
                            pass
                    diagnostics.put(self._sanitize(exc, 'worker_a'))
                finally:
                    if acr is not None:
                        try:
                            acr.close()
                        except Exception:
                            pass

            def worker_b_fn():
                bcr = None
                try:
                    threading.current_thread().dbname = dbname
                    bcr = self._open_bounded(dbname)
                    result['b_pid'] = self._backend_pid(bcr)
                    benv = api.Environment(bcr, SUPERUSER_ID, {})
                    # A genuine competing claim, WHILE A holds the reacquired lock.
                    claimed = benv['shopify.connector.job']._claim_for_dispatch(1)
                    result['b_claimed_ids'] = list(claimed.ids)
                    bcr.rollback()
                except BaseException as exc:
                    if bcr is not None:
                        try:
                            bcr.rollback()
                        except Exception:
                            pass
                    diagnostics.put(self._sanitize(exc, 'worker_b'))
                finally:
                    b_done.set()
                    if bcr is not None:
                        try:
                            bcr.close()
                        except Exception:
                            pass

            a_parked = False
            with patch.object(registry_cls, '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)), \
                    patch.object(ClientCls, '_send', ok_send), \
                    patch.object(DispatchCls, '_route_failure',
                                 parking_route_failure), \
                    patch.object(
                        DispatchCls, '_get_handlers',
                        lambda self: {
                            'core_dispatch_selftest': conflicting_selftest}):
                worker_a = threading.Thread(target=worker_a_fn, daemon=True)
                worker_a.start()
                a_parked = a_holds_lock.acquire(timeout=self.BOUND_SECONDS)
                if a_parked:
                    worker_b = threading.Thread(target=worker_b_fn, daemon=True)
                    worker_b.start()
                    worker_b.join(timeout=self.BOUND_SECONDS)
                b_done.set()   # release A regardless (defensive)
                worker_a.join(timeout=self.BOUND_SECONDS)
                self._assert_workers_dead((worker_a, worker_b))

            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(
                a_parked, 'Worker A never reacquired the lock + parked in bound')
            # Worker B genuinely raced the claim while A held the reacquired lock
            # and was SKIP-LOCKED out -- it obtained NOTHING (no dispatch).
            self.assertEqual(
                result.get('b_claimed_ids'), [],
                'the losing worker must obtain no post-rollback claim; saw %s'
                % result.get('b_claimed_ids'))
            # Exactly one transport total (A once; B never dispatched).
            self.assertEqual(
                len(send_tokens), 1, 'total transport must remain exactly one')
            self.assertIn(psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes)
            self.assertIsNotNone(result.get('a_pid'))
            self.assertIsNotNone(result.get('b_pid'))
            self.assertNotEqual(
                result['a_pid'], result['b_pid'],
                'the two workers ran on genuinely distinct backends')
            # The job reaches one deterministic safe state (A's single route).
            job_state, _rc = self._observe_job(dbname, job_id)
            self.assertEqual(
                job_state, 'retry_waiting',
                'the job must reach one deterministic safe state; saw %s'
                % job_state)
            self.assertEqual(
                self._lease_count(dbname, store_id), 0,
                'no lease / partial business data remains')
        finally:
            b_done.set()
            for t in (worker_a, worker_b):
                if t is not None:
                    t.join(timeout=self.BOUND_SECONDS)
            self._cleanup(dbname, store_id)

    # ------------------------------------------------------------------
    # Test C -- retry/exhaustion + ownership refusal
    # ------------------------------------------------------------------

    def test_c_conflict_exhaustion_routes_to_failed_final_after_reacquire(self):
        """Test C (exhaustion) -- when the bounded retry budget is already spent,
        the conflict path, reached ONLY after reacquiring the exact job lock,
        routes the job to the terminal ``failed_final`` state (not a raw error,
        not a replay) and persists the exhausted attempt count."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        conflict = {}
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(
                dbname, retry_counts=[RETRY_MAX_ATTEMPTS])
            job_id = job_ids[0]
            ClientCls = type(self.env['shopify.connector.api.client'])
            DispatchCls = type(self.env['shopify.connector.job.dispatch'])

            def ok_send(client_self, s, body, token=None):
                send_tokens.append(token)
                if 'pid' not in conflict:
                    self._commit_benign_store_bump(dbname, store_id, conflict)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def conflicting_selftest(job):
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    try:
                        job.store_id._lock_store_for_lifecycle()
                    except psycopg2.OperationalError as exc:
                        pgcodes.append(getattr(exc, 'pgcode', None))
                        raise

            drain_cr = self._open_bounded(dbname)
            try:
                drain_env = api.Environment(drain_cr, SUPERUSER_ID, {})
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)), \
                     patch.object(ClientCls, '_send', ok_send), \
                     patch.object(
                         DispatchCls, '_get_handlers',
                         lambda self: {
                             'core_dispatch_selftest': conflicting_selftest}):
                    drain_env['shopify.connector.job.dispatch'].run_drain(1)
            finally:
                drain_cr.close()

            self.assertEqual(len(send_tokens), 1, 'exactly one transport')
            self.assertIn(psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes)
            job_state, retry_count = self._observe_job(dbname, job_id)
            self.assertEqual(
                job_state, 'failed_final',
                'an exhausted-budget conflict must route (under the reacquired '
                'lock) to the terminal failed_final state; saw %s' % job_state)
            self.assertEqual(
                retry_count, RETRY_MAX_ATTEMPTS + 1,
                'the exhausted attempt count is persisted')
            self.assertEqual(self._lease_count(dbname, store_id), 0)
        finally:
            self._cleanup(dbname, store_id)

    def test_c_recovery_refuses_to_overwrite_a_job_worker_b_completed(self):
        """Test C (ownership) -- if, during A's reset window (after A rolled back,
        before A reacquires), Worker B genuinely claims and COMPLETES the job, A's
        recovery reacquires the exact row, sees a non-claimable (terminal) state
        under the lock, and does NOTHING: B's outcome is never overwritten, no
        duplicate transition is written, and A ends without error."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        pgcodes = []
        conflict = {}
        result = {}
        diagnostics = queue.Queue()
        a_at_reacquire = threading.Semaphore(0)
        b_done = threading.Event()
        registry_cls = type(self.registry)
        ClientCls = type(self.env['shopify.connector.api.client'])
        DispatchCls = type(self.env['shopify.connector.job.dispatch'])
        JobCls = type(self.env['shopify.connector.job'])
        real_try_lock = JobCls.try_lock_for_update
        worker_a = worker_b = None
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(dbname)
            job_id = job_ids[0]

            def dual_send(client_self, s, body, token=None):
                # Only Worker A transports (Worker B's handler is a clean no-op).
                send_tokens.append(token)
                threading.current_thread().transported = True
                if getattr(threading.current_thread(), 'is_worker_a', False) \
                        and 'pid' not in conflict:
                    self._commit_benign_store_bump(dbname, store_id, conflict)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def dual_selftest(job):
                if getattr(threading.current_thread(), 'is_worker_a', False):
                    Client = job.env['shopify.connector.api.client']
                    with Client.execute_business(job, job.store_id, 'q'):
                        try:
                            job.store_id._lock_store_for_lifecycle()
                        except psycopg2.OperationalError as exc:
                            pgcodes.append(getattr(exc, 'pgcode', None))
                            raise
                # Worker B: clean success, NO transport, NO conflict.

            def gated_try_lock(recs, *args, **kwargs):
                th = threading.current_thread()
                if getattr(th, 'park_reacquire', False) \
                        and getattr(th, 'transported', False):
                    th.transported = False   # park once (the recovery reacquire)
                    a_at_reacquire.release()
                    if not b_done.wait(timeout=self.BOUND_SECONDS):
                        raise AssertionError('b_done not set within bound')
                return real_try_lock(recs, *args, **kwargs)

            def worker_a_fn():
                acr = None
                try:
                    th = threading.current_thread()
                    th.is_worker_a = True
                    th.park_reacquire = True
                    th.dbname = dbname
                    acr = self._open_bounded(dbname)
                    result['a_pid'] = self._backend_pid(acr)
                    aenv = api.Environment(acr, SUPERUSER_ID, {})
                    aenv['shopify.connector.job.dispatch'].run_drain(1)
                    acr.commit()
                except BaseException as exc:
                    if acr is not None:
                        try:
                            acr.rollback()
                        except Exception:
                            pass
                    diagnostics.put(self._sanitize(exc, 'worker_a'))
                finally:
                    if acr is not None:
                        try:
                            acr.close()
                        except Exception:
                            pass

            def worker_b_fn():
                bcr = None
                try:
                    threading.current_thread().dbname = dbname
                    bcr = self._open_bounded(dbname)
                    result['b_pid'] = self._backend_pid(bcr)
                    benv = api.Environment(bcr, SUPERUSER_ID, {})
                    benv['shopify.connector.job.dispatch'].run_drain(1)
                    bcr.commit()
                    result['b_ok'] = True
                except BaseException as exc:
                    if bcr is not None:
                        try:
                            bcr.rollback()
                        except Exception:
                            pass
                    diagnostics.put(self._sanitize(exc, 'worker_b'))
                finally:
                    b_done.set()
                    if bcr is not None:
                        try:
                            bcr.close()
                        except Exception:
                            pass

            a_parked = False
            with patch.object(registry_cls, '_lock', threading.RLock()), \
                    patch.object(self.registry, 'cursor',
                                 self._real_registry_cursor(dbname)), \
                    patch.object(ClientCls, '_send', dual_send), \
                    patch.object(JobCls, 'try_lock_for_update', gated_try_lock), \
                    patch.object(
                        DispatchCls, '_get_handlers',
                        lambda self: {'core_dispatch_selftest': dual_selftest}):
                worker_a = threading.Thread(target=worker_a_fn, daemon=True)
                worker_a.start()
                a_parked = a_at_reacquire.acquire(timeout=self.BOUND_SECONDS)
                if a_parked:
                    worker_b = threading.Thread(target=worker_b_fn, daemon=True)
                    worker_b.start()
                    worker_b.join(timeout=self.BOUND_SECONDS)
                b_done.set()
                worker_a.join(timeout=self.BOUND_SECONDS)
                self._assert_workers_dead((worker_a, worker_b))

            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(
                a_parked, 'Worker A never parked before its recovery reacquire')
            self.assertTrue(result.get('b_ok'), 'Worker B did not complete')
            # Worker B completed the job; Worker A did NOT overwrite it.
            job_state, _rc = self._observe_job(dbname, job_id)
            self.assertEqual(
                job_state, 'succeeded',
                "Worker B's completed job must not be overwritten by A's "
                'recovery; saw %s' % job_state)
            # Exactly one transport (A's; B's handler never transported).
            self.assertEqual(
                len(send_tokens), 1,
                'only Worker A transported; B ran a clean no-op success')
            self.assertIn(psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes)
            self.assertIsNotNone(result.get('a_pid'))
            self.assertIsNotNone(result.get('b_pid'))
            self.assertNotEqual(result['a_pid'], result['b_pid'])
            self.assertEqual(self._lease_count(dbname, store_id), 0)
        finally:
            b_done.set()
            for t in (worker_a, worker_b):
                if t is not None:
                    t.join(timeout=self.BOUND_SECONDS)
            self._cleanup(dbname, store_id)

    # ------------------------------------------------------------------
    # Test D -- batch integrity across a per-job-committed drain
    # ------------------------------------------------------------------

    def test_d_batch_integrity_neighbor_conflict_preserves_committed_jobs(self):
        """Test D -- per-job commit integrity across a batch. Job 1 succeeds and
        commits once; Job 2 hits a genuine 40001 and is routed once to the bounded
        conflict state; Job 2's rollback cannot undo Job 1 (nor re-transport it),
        and a later eligible Job 3 is still processed. Each job's handler runs
        exactly once -- no replay anywhere in the batch."""
        dbname = self.env.cr.dbname
        store_id = None
        send_tokens = []
        handler_jobs = []
        pgcodes = []
        conflict = {}
        try:
            store_id, shop_domain, job_ids = self._commit_store_with_jobs(
                dbname, n_jobs=3)
            job1, job2, job3 = job_ids   # id asc == claim order
            ClientCls = type(self.env['shopify.connector.api.client'])
            DispatchCls = type(self.env['shopify.connector.job.dispatch'])

            def ok_send(client_self, s, body, token=None):
                send_tokens.append(token)
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def batch_selftest(job):
                handler_jobs.append(job.id)   # one entry per handler invocation
                Client = job.env['shopify.connector.api.client']
                with Client.execute_business(job, job.store_id, 'q'):
                    if job.id == job2:
                        # Only Job 2 conflicts. Its REPEATABLE READ snapshot began
                        # at its OWN claim (Job 1 already committed), so the benign
                        # bump + FOR NO KEY UPDATE aborts ONLY Job 2.
                        if 'pid' not in conflict:
                            self._commit_benign_store_bump(
                                dbname, store_id, conflict)
                        try:
                            job.store_id._lock_store_for_lifecycle()
                        except psycopg2.OperationalError as exc:
                            pgcodes.append(getattr(exc, 'pgcode', None))
                            raise

            drain_cr = self._open_bounded(dbname)
            try:
                drain_pid = self._backend_pid(drain_cr)
                drain_env = api.Environment(drain_cr, SUPERUSER_ID, {})
                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)), \
                     patch.object(ClientCls, '_send', ok_send), \
                     patch.object(
                         DispatchCls, '_get_handlers',
                         lambda self: {
                             'core_dispatch_selftest': batch_selftest}):
                    drain_env['shopify.connector.job.dispatch'].run_drain(3)
            finally:
                drain_cr.close()

            # Each job's handler ran exactly once, in claim order -- no replay.
            self.assertEqual(
                handler_jobs, [job1, job2, job3],
                'each job handled once, in claim order, none replayed; saw %s'
                % handler_jobs)
            # One transport per job, three total -- Job 1 never re-transported by
            # Job 2's rollback.
            self.assertEqual(
                len(send_tokens), 3, 'one transport per job; no job re-transported')
            self.assertIn(psycopg2.errorcodes.SERIALIZATION_FAILURE, pgcodes)
            self.assertIn('pid', conflict)
            self.assertNotEqual(conflict['pid'], drain_pid)
            # Job 1 committed once and survived Job 2's rollback.
            self.assertEqual(
                self._observe_job(dbname, job1)[0], 'succeeded',
                "Job 1's committed success must survive Job 2's rollback")
            # Job 2 reached the selected safe conflict state.
            self.assertEqual(
                self._observe_job(dbname, job2)[0], 'retry_waiting',
                'Job 2 must reach the bounded conflict retry state')
            # A later eligible job was still processed after the conflict.
            self.assertEqual(
                self._observe_job(dbname, job3)[0], 'succeeded',
                'a later eligible job must still be processed')
            self.assertEqual(self._lease_count(dbname, store_id), 0)
        finally:
            self._cleanup(dbname, store_id)
