import ast
import os
import re
from pathlib import Path

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_job_dispatch
from ..models import shopify_connector_mutation_attempt


RAW_HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'request'}
GRAPHQL_MUTATION_LITERAL = re.compile(
    r'(?:^|[\r\n])\s*mutation\s+[A-Za-z_][A-Za-z0-9_]*\s*[({]'
)
EXCEPTION_SUPERCLASSES = {
    'ValidationError': frozenset({'UserError', 'Exception', 'BaseException'}),
    'AccessError': frozenset({'UserError', 'Exception', 'BaseException'}),
    'UserError': frozenset({'Exception', 'BaseException'}),
    'Exception': frozenset({'BaseException'}),
}
BASE_EXCEPTION_ONLY = frozenset({
    'BaseException', 'GeneratorExit', 'KeyboardInterrupt', 'SystemExit',
})


def _parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _owning_method(node, parents):
    owner = parents.get(node)
    while owner and not isinstance(owner, ast.FunctionDef):
        owner = parents.get(owner)
    return owner


# The ONLY accepted prepare/transport production split (Task 013 Track B,
# PR #182 comment 5031833846). The GraphQL mutation operation literal is
# built in the `_prepare_preconditions_*` method, while the single guarded
# `client.execute_business(..., mutation_context=...)` call lives in the
# paired `_transport_*` method of the *same* class. This allowlist is exact
# and narrow -- an unknown file, class, prepare method, or transport sibling
# is never accepted here; it falls through to the default same-method guard
# and is reported as a violation. Keyed by
# (addon-relative file suffix, class name, prepare method)
#   -> the exact transport sibling that must hold the guarded call.
ACCEPTED_PREPARE_TRANSPORT_SPLIT = {
    (
        'shopify_connector_inventory/models/'
        'shopify_connector_inventory_service.py',
        'ShopifyConnectorInventoryService',
        '_prepare_preconditions_set_quantities',
    ): '_transport_set_quantities',
    (
        'shopify_connector_inventory/models/'
        'shopify_connector_inventory_service.py',
        'ShopifyConnectorInventoryService',
        '_prepare_preconditions_activate',
    ): '_transport_activate',
}


def _owning_class(node, parents):
    owner = parents.get(node)
    while owner and not isinstance(owner, ast.ClassDef):
        owner = parents.get(owner)
    return owner


def _method_has_guarded_execute_business(method_node):
    """True when the method contains a `.execute_business(...)` call that
    passes a `mutation_context=` keyword argument."""
    if method_node is None:
        return False
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == 'execute_business'
        and any(keyword.arg == 'mutation_context' for keyword in call.keywords)
        for call in ast.walk(method_node)
    )


def _method_has_forbidden_transport(method_node):
    """True when the method reaches transport by any route other than the
    guarded business surface: a `.execute(...)` / `._send(...)` attribute
    call, or a raw `requests.<verb>(...)` HTTP call."""
    if method_node is None:
        return False
    for call in ast.walk(method_node):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
        ):
            continue
        if call.func.attr in {'execute', '_send'}:
            return True
        if (
            call.func.attr in RAW_HTTP_METHODS
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == 'requests'
        ):
            return True
    return False


def _accepted_split_transport_name(relative, class_name, method_name):
    """Return the exact transport sibling name for an accepted split, or
    None when (file, class, prepare method) is not on the allowlist."""
    for (file_suffix, cls, prepare), transport in (
        ACCEPTED_PREPARE_TRANSPORT_SPLIT.items()
    ):
        if (
            relative.endswith(file_suffix)
            and class_name == cls
            and method_name == prepare
        ):
            return transport
    return None


def _single_paired_transport(owner_class, paired_name):
    """Return the paired transport method of `owner_class` named
    `paired_name`, but only when it exists *exactly once*; else None."""
    if owner_class is None:
        return None
    siblings = [
        member for member in owner_class.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and member.name == paired_name
    ]
    if len(siblings) != 1:
        return None
    return siblings[0]


def _mutation_literal_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    parents = _parent_map(tree)
    violations = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and GRAPHQL_MUTATION_LITERAL.search(node.value)
        ):
            continue
        owner = _owning_method(node, parents)
        owner_name = owner.name if owner else False
        owner_class = _owning_class(node, parents)
        owner_class_name = owner_class.name if owner_class else False
        selftest = (
            relative.endswith(
                'shopify_connector_core/models/'
                'shopify_connector_job_dispatch.py'
            )
            and owner_name == '_prepare_preconditions_mutation_selftest'
        )
        if selftest:
            continue

        # Default (unchanged): the guarded `execute_business(
        # mutation_context=...)` call must live in the *same* method that
        # holds the literal, and that method must not reach transport by
        # any forbidden route.
        if (
            _method_has_guarded_execute_business(owner)
            and not _method_has_forbidden_transport(owner)
        ):
            continue

        # Accepted prepare/transport split -- exact, narrow allowlist only.
        # Every one of these must hold, or the literal is a violation:
        #   * (file, class, prepare method) is on the allowlist;
        #   * the paired transport method exists exactly once in the SAME
        #     class;
        #   * the transport method holds `execute_business(mutation_context
        #     =...)`;
        #   * neither the prepare nor the transport method reaches transport
        #     by a forbidden route (`.execute` / `._send` / raw HTTP).
        paired_name = _accepted_split_transport_name(
            relative, owner_class_name, owner_name,
        )
        if paired_name is not None:
            transport = _single_paired_transport(owner_class, paired_name)
            if (
                transport is not None
                and not _method_has_forbidden_transport(owner)
                and _method_has_guarded_execute_business(transport)
                and not _method_has_forbidden_transport(transport)
            ):
                continue

        violations.append((relative, node.lineno, owner_name))
    return violations


def _contains_attempt_env_lookup(node):
    return any(
        isinstance(part, ast.Subscript)
        and isinstance(part.slice, ast.Constant)
        and part.slice.value == 'shopify.connector.mutation.attempt'
        for part in ast.walk(node)
    )


def _attempt_write_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    parents = _parent_map(tree)
    allowed = {
        'create', 'write', '_create_attempt_intent',
        '_record_direct_outcome', '_record_recovery_uncertain',
        '_record_reconciliation_result',
        '_record_inconclusive_reconciliation',
        'action_resolve_mutation_attempt', '_mask_terminal_evidence',
    }
    violations = []
    attempt_model_file = relative.endswith(
        'shopify_connector_core/models/'
        'shopify_connector_mutation_attempt.py'
    )
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {'create', 'write', 'unlink'}
        ):
            continue
        target = node.func.value
        target_source = ast.unparse(target)
        root_names = {
            part.id.lower() for part in ast.walk(target)
            if isinstance(part, ast.Name)
        }
        is_attempt_target = (
            bool(root_names & {'attempt', 'attempts'})
            or _contains_attempt_env_lookup(target)
            or '._surface(' in target_source
            or (
                attempt_model_file
                and ('self' in root_names or target_source.startswith('super()'))
            )
        )
        if not is_attempt_target:
            continue
        owner = _owning_method(node, parents)
        owner_name = owner.name if owner else False
        if node.func.attr == 'create':
            sanctioned = (
                attempt_model_file
                and owner_name in {'create', '_create_attempt_intent'}
            )
        elif node.func.attr == 'write':
            sanctioned = attempt_model_file and owner_name in allowed
        else:
            sanctioned = False
        if not sanctioned:
            violations.append((
                relative, node.lineno, owner_name,
                node.func.attr, target_source,
            ))
    return violations


def _exception_handler_names(handler_type):
    if handler_type is None:
        return ('BaseException',)
    if isinstance(handler_type, ast.Tuple):
        return tuple(
            name
            for item in handler_type.elts
            for name in _exception_handler_names(item)
        )
    return (ast.unparse(handler_type),)


def _exception_handler_shadows(earlier, later):
    if earlier == later or earlier == 'BaseException':
        return True
    if earlier == 'Exception' and later not in BASE_EXCEPTION_ONLY:
        return True
    return earlier in EXCEPTION_SUPERCLASSES.get(later, frozenset())


def _exception_shadowing_violations(source, relative):
    tree = ast.parse(source, filename=relative)
    violations = []
    for try_node in ast.walk(tree):
        if not isinstance(try_node, (ast.Try, ast.TryStar)):
            continue
        earlier_names = []
        for handler in try_node.handlers:
            later_names = _exception_handler_names(handler.type)
            for later in later_names:
                for earlier in earlier_names:
                    if _exception_handler_shadows(earlier, later):
                        violations.append((
                            relative, handler.lineno, earlier, later,
                        ))
            earlier_names.extend(later_names)
    return violations


# --- Synthetic-source builders for the accepted-split adversarial tests ---

_INV_SPLIT_FILE = (
    'shopify_connector_inventory/models/'
    'shopify_connector_inventory_service.py'
)
_INV_SPLIT_CLASS = 'ShopifyConnectorInventoryService'


def _make_split_source(
    *,
    class_name=_INV_SPLIT_CLASS,
    prepare_name='_prepare_preconditions_set_quantities',
    transport_name='_transport_set_quantities',
    include_transport=True,
    transport_call='execute_business',
    context_keyword='mutation_context',
    prepare_forbidden=None,
    transport_forbidden=None,
):
    """Build a minimal, syntactically valid module source that mirrors the
    real accepted prepare/transport split, with exactly one knob varied per
    adversarial case. Defaults produce a *valid* accepted split."""
    prepare_extra = (
        '        %s\n' % prepare_forbidden if prepare_forbidden else ''
    )
    src = (
        'class %s:\n'
        '    def %s(self, local_snapshot, owner_context):\n'
        "        operation = 'mutation InventorySetQuantities($input: X!)"
        " { x }'\n"
        '%s'
        "        return {'operation': operation}\n"
    ) % (class_name, prepare_name, prepare_extra)
    if include_transport:
        transport_extra = (
            '        %s\n' % transport_forbidden if transport_forbidden else ''
        )
        if transport_call == 'execute_business':
            call_block = (
                '        with client.execute_business(\n'
                "            attempt_context['job_id'], store,\n"
                "            request['operation'], request['variables'],\n"
                '            %s=attempt_context,\n'
                '        ) as result:\n'
                '            return result\n'
            ) % (context_keyword,)
        else:
            call_block = (
                '        return client.%s(store, request)\n' % transport_call
            )
        src += (
            '    def %s(self, request, attempt_context):\n'
            "        client = self.env['shopify.connector.api.client']\n"
            '        store = client\n'
            '%s'
            '%s'
        ) % (transport_name, transport_extra, call_block)
    return src


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestMutationSourceGuards(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[2]

    def _python_files(self):
        return sorted(
            path for path in self._addon_root().glob(
                'shopify_connector_*/**/*.py'
            )
            if 'tests' not in path.parts
        )

    def test_repo_wide_raw_transport_guard(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr in RAW_HTTP_METHODS
                    and isinstance(func.value, ast.Name)
                    and func.value.id == 'requests'
                ):
                    continue
                relative = str(path.relative_to(self._addon_root()))
                owner = parents.get(node)
                while owner and not isinstance(owner, ast.FunctionDef):
                    owner = parents.get(owner)
                owner_name = owner.name if owner else False
                allowed = (
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_api_client.py'
                    )
                    and func.attr == 'post'
                    and owner_name == '_send'
                ) or (
                    relative.endswith(
                        'shopify_connector_product/models/'
                        'shopify_connector_product_importer.py'
                    )
                    and func.attr == 'get'
                )
                if not allowed:
                    violations.append((relative, node.lineno, func.attr))
        self.assertFalse(violations, violations)

    def test_mutation_literals_require_guarded_transport_or_selftest(self):
        violations = []
        for path in self._python_files():
            relative = str(path.relative_to(self._addon_root()))
            violations.extend(_mutation_literal_violations(
                path.read_text(encoding='utf-8'), relative,
            ))
        self.assertFalse(violations, violations)

    def test_mutation_literal_detector_rejects_unguarded_paths(self):
        for call in (
            "return self.execute(store, operation)",
            "return self._send(store, {'query': operation})",
            'return operation',
        ):
            source = (
                'def unsafe(self, store):\n'
                "    operation = 'mutation Unsafe($id: ID!) { x }'\n"
                '    %s\n' % call
            )
            self.assertTrue(_mutation_literal_violations(
                source, 'shopify_connector_core/models/unsafe.py',
            ))
        guarded = (
            'def guarded(self, client, job, store, context):\n'
            "    operation = 'mutation Guarded($id: ID!) { x }'\n"
            '    with client.execute_business(\n'
            '        job, store, operation, {}, mutation_context=context,\n'
            '    ):\n'
            '        pass\n'
        )
        self.assertFalse(_mutation_literal_violations(
            guarded, 'shopify_connector_domain/models/exporter.py',
        ))

    # --- Accepted prepare/transport split: adversarial guard self-tests ---

    def test_accepted_split_allowlist_is_exactly_the_two_inventory_pairs(self):
        # The allowlist must stay exact and narrow: exactly the two real
        # inventory pairs, nothing else. This fails if anyone widens it
        # (e.g. to every `_prepare_preconditions_*`).
        self.assertEqual(
            ACCEPTED_PREPARE_TRANSPORT_SPLIT,
            {
                (
                    _INV_SPLIT_FILE, _INV_SPLIT_CLASS,
                    '_prepare_preconditions_set_quantities',
                ): '_transport_set_quantities',
                (
                    _INV_SPLIT_FILE, _INV_SPLIT_CLASS,
                    '_prepare_preconditions_activate',
                ): '_transport_activate',
            },
        )

    def test_accepted_split_real_inventory_service_passes(self):
        # The REAL production file: both accepted prepare/transport pairs
        # must be recognised, producing zero mutation-literal violations.
        # Guarded against vacuity: the two GraphQL mutation literals and the
        # guarded transport surface must genuinely exist in the file, and
        # the two prepare methods must NOT themselves hold `execute_business`
        # (so the only way they pass is via the accepted split).
        root = self._addon_root()
        path = (
            root / 'shopify_connector_inventory' / 'models'
            / 'shopify_connector_inventory_service.py'
        )
        source = path.read_text(encoding='utf-8')
        relative = str(path.relative_to(root))
        self.assertIn('mutation InventorySetQuantities', source)
        self.assertIn('mutation InventoryActivate', source)
        tree = ast.parse(source)
        prepare_methods = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in {
                '_prepare_preconditions_set_quantities',
                '_prepare_preconditions_activate',
            }
        }
        self.assertEqual(len(prepare_methods), 2)
        for method in prepare_methods.values():
            self.assertFalse(
                _method_has_guarded_execute_business(method),
                'prepare method unexpectedly holds the guarded call; the '
                'split test would be vacuous',
            )
        self.assertEqual(_mutation_literal_violations(source, relative), [])

    def test_accepted_split_both_synthetic_pairs_pass(self):
        for prepare, transport, literal in (
            ('_prepare_preconditions_set_quantities',
             '_transport_set_quantities', 'InventorySetQuantities'),
            ('_prepare_preconditions_activate',
             '_transport_activate', 'InventoryActivate'),
        ):
            source = _make_split_source(
                prepare_name=prepare, transport_name=transport,
            ).replace('InventorySetQuantities', literal)
            self.assertEqual(
                _mutation_literal_violations(source, _INV_SPLIT_FILE), [],
                (prepare, transport),
            )

    def test_split_missing_transport_sibling_fails(self):
        source = _make_split_source(include_transport=False)
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_wrong_transport_sibling_name_fails(self):
        # prepare_set_quantities paired only with the WRONG sibling
        # (_transport_activate) -- the expected _transport_set_quantities
        # is absent.
        source = _make_split_source(
            prepare_name='_prepare_preconditions_set_quantities',
            transport_name='_transport_activate',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_wrong_class_fails(self):
        source = _make_split_source(class_name='SomeOtherModel')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_unlisted_file_fails(self):
        # Same-shaped valid split, but in a file that is not on the
        # allowlist.
        source = _make_split_source()
        self.assertTrue(_mutation_literal_violations(
            source, 'shopify_connector_other/models/external.py',
        ))

    def test_split_transport_without_execute_business_fails(self):
        source = _make_split_source(transport_call='dispatch')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_missing_mutation_context_fails(self):
        source = _make_split_source(context_keyword='business_context')
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_execute_fails(self):
        # Guarded call present, but the transport also reaches raw
        # `.execute(...)` -- forbidden route.
        source = _make_split_source(
            transport_forbidden='client.execute(store, request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_send_fails(self):
        source = _make_split_source(
            transport_forbidden='client._send(store, request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_prepare_using_forbidden_transport_fails(self):
        # The prepare method itself must not reach transport.
        source = _make_split_source(
            prepare_forbidden='self.env["x"]._send(store, operation)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_split_transport_using_raw_http_fails(self):
        source = _make_split_source(
            transport_forbidden='requests.post(url, json=request)',
        )
        self.assertTrue(
            _mutation_literal_violations(source, _INV_SPLIT_FILE),
        )

    def test_no_production_direct_send_caller(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'))
            relative = str(path.relative_to(self._addon_root()))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == '_send'
                ):
                    continue
                if not relative.endswith(
                    'shopify_connector_core/models/'
                    'shopify_connector_api_client.py'
                ):
                    violations.append((relative, node.lineno))
        self.assertFalse(violations, violations)

    def test_attempt_write_surface_is_closed_and_unlink_forbidden(self):
        source = Path(
            shopify_connector_mutation_attempt.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        class_node = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == 'ShopifyConnectorMutationAttempt'
        )
        methods = {
            node.name for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required = {
            '_create_attempt_intent',
            '_record_direct_outcome',
            '_record_recovery_uncertain',
            '_record_reconciliation_result',
            '_record_inconclusive_reconciliation',
            'action_resolve_mutation_attempt',
            '_mask_terminal_evidence',
        }
        self.assertTrue(required <= methods)
        self.assertIn('unlink', methods)
        self.assertIn('can never be deleted', source)

    def test_no_attempt_direct_write_call_outside_closed_surface(self):
        violations = []
        for path in self._python_files():
            relative = str(path.relative_to(self._addon_root()))
            violations.extend(_attempt_write_violations(
                path.read_text(encoding='utf-8'), relative,
            ))
        self.assertFalse(violations, violations)

    def test_attempt_write_detector_distinguishes_real_targets(self):
        bad_sources = (
            "def bad(self, attempt):\n    attempt.write({'x': 1})\n",
            "def bad(self, attempts):\n    attempts.unlink()\n",
            "def bad(self):\n"
            "    self.env['shopify.connector.mutation.attempt'].create({})\n",
            "def bad(self, other):\n"
            "    other._surface('forged').write({'x': 1})\n",
        )
        for source in bad_sources:
            self.assertTrue(_attempt_write_violations(
                source, 'shopify_connector_core/models/unsafe.py',
            ))
        unrelated = (
            "def ok(self):\n"
            "    self.write({'state': 'connected'})\n"
        )
        self.assertFalse(_attempt_write_violations(
            unrelated, 'shopify_connector_core/models/store.py',
        ))

    def test_attempt_write_detector_rejects_external_same_named_methods(self):
        external = (
            "def _record_direct_outcome(self, attempt):\n"
            "    attempt.write({'observed_outcome': 'succeeded'})\n",
            "def action_resolve_mutation_attempt(self, attempt):\n"
            "    attempt._surface('forged').write({'resolved_at': None})\n",
            "def _create_attempt_intent(self):\n"
            "    return self.env[\n"
            "        'shopify.connector.mutation.attempt'\n"
            "    ].create({})\n",
        )
        for source in external:
            violations = _attempt_write_violations(
                source, 'shopify_connector_other/models/external.py',
            )
            self.assertTrue(violations, source)

    def test_write_surface_inventory_is_exact(self):
        self.assertEqual(
            shopify_connector_mutation_attempt.WRITE_SURFACES,
            frozenset({
                '_record_direct_outcome',
                '_record_recovery_uncertain',
                '_record_reconciliation_result',
                '_record_inconclusive_reconciliation',
                'action_resolve_mutation_attempt',
                '_mask_terminal_evidence',
            }),
        )

    def test_reconciliation_admission_has_only_uncertain_owners(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        owners = set()
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == '_ensure_reconciliation_job'
            ):
                continue
            owner = parents.get(node)
            while owner and not isinstance(owner, ast.FunctionDef):
                owner = parents.get(owner)
            owners.add(owner.name if owner else False)
        self.assertEqual(owners, {
            '_apply_validated_consequence',
            '_recover_committed_attempt_to_reconciliation',
        })

    def test_dispatch_exception_handlers_are_not_shadowed(self):
        path = Path(shopify_connector_job_dispatch.__file__)
        self.assertFalse(_exception_shadowing_violations(
            path.read_text(encoding='utf-8'), str(path),
        ))

    def test_exception_shadowing_detector_rejects_superclass_first(self):
        self.assertTrue(issubclass(ValidationError, UserError))
        self.assertTrue(issubclass(AccessError, UserError))
        invalid = '''
try:
    recover()
except UserError:
    refuse_owner()
except ValidationError:
    block_invalid_state()
'''
        violations = _exception_shadowing_violations(
            invalid, 'synthetic_invalid_recovery.py',
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][2:], ('UserError', 'ValidationError'))

    def test_exception_shadowing_detector_accepts_specific_first(self):
        valid = '''
try:
    recover()
except (ValidationError, AccessError):
    block_invalid_state()
except UserError:
    refuse_owner()
except Exception:
    fail_closed()
'''
        self.assertFalse(_exception_shadowing_violations(
            valid, 'synthetic_valid_recovery.py',
        ))

    def test_zero_real_mutation_domain_and_calls(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        self.assertNotIn('inventorySetQuantities', source)
        self.assertNotIn('inventoryActivate', source)
        self.assertNotIn('fulfillmentCreate', source)
        self.assertIn("'transport': 'synthetic_stub'", source)
        self.assertNotIn('_get_access_token', source)
        self.assertNotIn('requests.', source)

    def test_exact_strategy_shape_and_process_death_escape(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        expected = {
            'reconciliation_job_type', 'prepare_local',
            'prepare_preconditions', 'transport',
            'classify_direct_result', 'reconcile', 'apply_consequence',
        }
        self.assertEqual(
            shopify_connector_job_dispatch.MUTATION_STRATEGY_KEYS,
            frozenset(expected),
        )
        wrapper = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_drain_mutation_one'
        )
        caught = {
            ast.unparse(handler.type)
            for handler in ast.walk(wrapper)
            if isinstance(handler, ast.ExceptHandler) and handler.type
        }
        self.assertNotIn('BaseException', caught)
        precondition = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_prepare_preconditions_mutation_selftest'
        )
        precondition_source = ast.unparse(precondition)
        self.assertNotIn('self.env', precondition_source)
        self.assertNotIn('_send', precondition_source)
