"""Issue #193 / #157 regression guard -- Odoo 19 test-phase contract.

Every connector test class must run in the ``post_install`` phase. See
``docs/05-qa/odoo19-test-phase-contract.md`` for the verified Odoo 19
mechanism; in short, a warm ``-u`` run has the ``NOT NULL`` column in
PostgreSQL but not yet the field in the registry, so an ``at_install``
fixture insert omits it and PostgreSQL rejects the row.

This guard is static (it parses the test sources) so it reports *every*
offending class at once instead of failing on whichever fixture happens to
run first, and so it works even in a runtime where the offending phase would
not be reached.
"""

import ast
import pathlib

from odoo.tests.common import TransactionCase, tagged

#: Odoo test base classes a connector test case can ultimately derive from.
ODOO_TEST_BASES = frozenset({
    'TransactionCase',
    'HttpCase',
    'SingleTransactionCase',
    'SavepointCase',
    'BaseCase',
})

#: Classes explicitly exempted from the contract, each with a recorded reason.
#: Only add a class here when it has a genuine, documented need to run at
#: install time AND its fixtures provably cannot hit the #193 NOT NULL family
#: (i.e. it creates no res.users / res.partner / product.template row, directly
#: or through the connector code it exercises). An exemption reintroduces the
#: failure family for that class if either condition stops holding.
EXEMPTIONS: dict[tuple[str, str], str] = {
    ('test_mutation_dispatch.py', 'TestMutationDispatch'): (
        'Asserts the core mutation registry is domain-neutral, which is only '
        'meaningful while inventory/fulfillment are NOT loaded. Creates only '
        'connector-owned rows (store/job/job.log), so it cannot hit the #193 '
        'NOT NULL family.'
    ),
}


def _connector_test_files():
    # .../addons/shopify_connector_core/tests/test_phase_contract.py
    #   parents[0] = tests, parents[1] = shopify_connector_core, parents[2] = addons
    addons = pathlib.Path(__file__).resolve().parents[2]
    return sorted(addons.glob('shopify_connector_*/tests/test_*.py'))


def _class_tags(node):
    tags = []
    for decorator in node.decorator_list:
        func = getattr(decorator, 'func', decorator)
        name = getattr(func, 'id', getattr(func, 'attr', None))
        if name != 'tagged':
            continue
        for arg in getattr(decorator, 'args', []):
            if isinstance(arg, ast.Constant):
                tags.append(arg.value)
    return tags


def _test_classes(path):
    """Yield ``(class_name, tags)`` for every real Odoo test case in *path*.

    Base-class resolution is transitive within the file so intermediate
    fixtures bases (``OrderImportCase``, ``_CustomerMatchingScalabilityBase``)
    correctly mark their subclasses as test cases.
    """
    tree = ast.parse(path.read_text())
    local = {
        node.name: [ast.unparse(base) for base in node.bases]
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }

    def derives_from_odoo_test(name, seen=()):
        if name in ODOO_TEST_BASES:
            return True
        if name in seen:
            return False
        for base in local.get(name, ()):
            simple = base.split('.')[-1].split('(')[0]
            if derives_from_odoo_test(simple, seen + (name,)):
                return True
        return False

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and derives_from_odoo_test(node.name):
            yield node.name, _class_tags(node)


@tagged('post_install', '-at_install')
class TestPhaseContract(TransactionCase):

    def test_every_connector_test_class_runs_post_install(self):
        """No connector test class may run in the at_install phase."""
        offenders = []
        for path in _connector_test_files():
            for cls, tags in _test_classes(path):
                key = (path.name, cls)
                if key in EXEMPTIONS:
                    continue
                if 'post_install' not in tags:
                    offenders.append(
                        '%s::%s (tags=%s)' % (path.name, cls, tags or 'none')
                    )
        self.assertFalse(
            offenders,
            'These connector test classes still run at_install and will fail a '
            'warm `-u` run with NOT NULL violations (issue #193/#157). Add '
            "@tagged('post_install', '-at_install'). Offenders:\n  "
            + '\n  '.join(offenders),
        )

    def test_post_install_classes_also_drop_at_install(self):
        """`post_install` without `-at_install` leaves both phases active.

        Odoo 19 unions `tagged` arguments onto the inherited default tag set
        ``{'standard', 'at_install'}``, so a class tagged only ``post_install``
        still runs at install time and still hits the #193 family.
        """
        offenders = []
        for path in _connector_test_files():
            for cls, tags in _test_classes(path):
                if 'post_install' in tags and '-at_install' not in tags:
                    offenders.append('%s::%s (tags=%s)' % (path.name, cls, tags))
        self.assertFalse(
            offenders,
            "These classes tag 'post_install' but do not remove the inherited "
            "'at_install', so they still run in both phases. Add '-at_install'. "
            'Offenders:\n  ' + '\n  '.join(offenders),
        )

    def test_guard_actually_discovers_the_connector_suite(self):
        """Fail loudly if the file discovery silently matches nothing."""
        files = _connector_test_files()
        self.assertGreater(
            len(files), 50,
            'Phase-contract guard found only %d connector test files; the '
            'discovery glob is wrong and the guard is vacuous.' % len(files),
        )
        total = sum(1 for path in files for _ in _test_classes(path))
        self.assertGreater(
            total, 80,
            'Phase-contract guard resolved only %d test classes; base-class '
            'resolution is broken and the guard is vacuous.' % total,
        )
