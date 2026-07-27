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
import re

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

    def test_every_nonstandard_class_is_selected_by_the_suite_runner(self):
        """Every `-standard` class must be reachable by the continuous runner.

        Eight connector test classes carry `-standard`, which is a legitimate
        Odoo mechanism for expensive or process-spawning tests -- but it also
        means `--test-enable` alone never selects them. That is exactly how four
        genuine concurrency proofs went unexecuted for four waves while the
        acceptance matrix recorded the suite as green (debt audit D-6).

        `tools/run_connector_suite.sh` now runs them as a third pass, driven by
        its `NONSTANDARD_TAGS` list. A hand-maintained list drifts, so this
        asserts the invariant directly: for every class that opts OUT of the
        standard phase, at least one of its remaining tags must appear in that
        list. Adding a `-standard` class without adding its tag fails here,
        rather than silently reintroducing an unrun test.
        """
        runner = (pathlib.Path(__file__).resolve().parents[3]
                  / 'tools' / 'run_connector_suite.sh')
        self.assertTrue(runner.is_file(), 'suite runner not found at %s' % runner)
        match = re.search(r'^NONSTANDARD_TAGS="([^"]*)"', runner.read_text(),
                          re.M)
        self.assertIsNotNone(
            match, 'NONSTANDARD_TAGS is not defined in the suite runner')
        covered = {tag.strip() for tag in match.group(1).split(',') if tag.strip()}

        unreachable = []
        nonstandard_seen = 0
        for path in _connector_test_files():
            for class_name, tags in _test_classes(path):
                if '-standard' not in tags:
                    continue
                nonstandard_seen += 1
                selectors = {tag for tag in tags if not tag.startswith('-')}
                if not selectors & covered:
                    unreachable.append('%s::%s (tags: %s)' % (
                        path.name, class_name, ', '.join(sorted(tags))))

        self.assertFalse(unreachable, (
            'These `-standard` test classes are not selected by any tag in '
            'run_connector_suite.sh NONSTANDARD_TAGS, so continuous validation '
            'would never execute them:\n  %s' % '\n  '.join(unreachable)))
        self.assertGreater(
            nonstandard_seen, 0,
            'No `-standard` class was discovered at all; this guard is vacuous.',
        )

    def test_every_tour_test_is_listed_in_the_suite_runner(self):
        """`REQUIRED_TOUR_TESTS` must equal the tours that actually exist.

        TD-010's fix makes `run_connector_suite.sh` FAIL when a required tour
        did not execute, which only means anything if the required list is the
        real list. A hand-maintained inventory drifts, so this asserts the
        invariant directly, exactly as
        `test_every_nonstandard_class_is_selected_by_the_suite_runner` does
        for the non-standard tags: every test method that calls `start_tour`
        must be named in the runner, and every name in the runner must exist.

        Adding a tour and forgetting the runner would otherwise reduce browser
        coverage silently -- which is the whole failure mode TD-010 is about.
        """
        runner = (pathlib.Path(__file__).resolve().parents[3]
                  / 'tools' / 'run_connector_suite.sh')
        self.assertTrue(runner.is_file(), 'suite runner not found at %s' % runner)
        match = re.search(r'^REQUIRED_TOUR_TESTS="\\\n(.*?)"',
                          runner.read_text(), re.M | re.S)
        self.assertIsNotNone(
            match, 'REQUIRED_TOUR_TESTS is not defined in the suite runner')
        listed = {entry.strip() for entry in match.group(1).split('\\\n')
                  if entry.strip()}

        actual = set()
        for path in _connector_test_files():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if not isinstance(item, (ast.FunctionDef,
                                             ast.AsyncFunctionDef)):
                        continue
                    if not item.name.startswith('test_'):
                        continue
                    # Match an actual CALL to `…start_tour(…)`, not the string
                    # "start_tour" appearing anywhere in the method. This guard
                    # names the identifier in its own body, so a substring
                    # search finds itself and reports a test that drives no
                    # tour as a missing tour -- which is exactly the kind of
                    # false positive that gets a guard deleted.
                    if any(
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'start_tour'
                        for call in ast.walk(item)
                        if isinstance(call, ast.Call)
                    ):
                        actual.add('%s.%s' % (node.name, item.name))

        self.assertTrue(
            actual, 'no test method calling start_tour was discovered at all; '
                    'this guard is vacuous')
        self.assertEqual(
            listed, actual,
            'run_connector_suite.sh REQUIRED_TOUR_TESTS disagrees with the '
            'tours in the repository.\n  only in the runner: %s\n  only in '
            'the tests: %s' % (sorted(listed - actual), sorted(actual - listed)),
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
