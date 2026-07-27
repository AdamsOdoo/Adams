"""Standing structural guards over this module and its UI layer.

These tests do not exercise behaviour; they hold the shape of the module so a
later edit cannot quietly reintroduce something the ruling forbids. The repo's
existing guards (the frozen sudo inventory, the phase contract, the UI
source guards) exist for the same reason and have each caught a real defect.
"""

import ast
import pathlib

from odoo.tests.common import tagged

from odoo.tests.common import TransactionCase

MODULE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _python_sources(include_tests=False):
    for path in sorted(MODULE_ROOT.rglob('*.py')):
        if not include_tests and 'tests' in path.parts:
            continue
        yield path


@tagged('post_install', '-at_install')
class TestExportSourceGuards(TransactionCase):

    # ------------------------------------------------------------------
    # The UI layer delegates and does nothing else
    # ------------------------------------------------------------------

    def test_wizards_never_write_create_sudo_commit_or_enqueue(self):
        """A display-and-delegate wizard that writes is no longer one.

        The U1/U2 precedent: the wizard collects an argument an object button
        cannot pass and calls a sanctioned server action. Anything else moves
        business logic into the UI layer, where none of the guards live.
        """
        wizard_dir = MODULE_ROOT / 'wizards'
        forbidden = {'create', 'write', 'unlink', 'sudo', 'commit', 'enqueue'}
        offenders = []
        for path in sorted(wizard_dir.rglob('*.py')):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Attribute) and (
                    node.func.attr in forbidden
                ):
                    offenders.append((path.name, node.func.attr, node.lineno))
        self.assertEqual(offenders, [], 'a wizard performs a write-side call')

    def test_no_view_file_contains_a_mutation_name(self):
        """Mutation logic never lives in XML.

        A GraphQL operation in a view would mean a screen builds a request,
        which puts a merchant's catalog behind an XML edit with no test and no
        Layer 2 attempt.
        """
        offenders = []
        for path in sorted((MODULE_ROOT / 'views').rglob('*.xml')):
            source = path.read_text()
            for token in (
                'productSet', 'productUpdate', 'productVariantsBulk',
                'fileCreate', 'fileUpdate', 'stagedUploadsCreate',
                'mutation ',
            ):
                if token in source:
                    offenders.append((path.name, token))
        self.assertEqual(offenders, [])

    # ------------------------------------------------------------------
    # Every sudo() in this module is accounted for
    # ------------------------------------------------------------------

    def test_the_sudo_inventory_is_frozen(self):
        """A new `sudo()` has to be added here deliberately.

        The same standing guard the core module carries: an unreviewed
        elevation is how an access boundary erodes one commit at a time. The
        count is per file so a diff shows exactly where a new one appeared.
        """
        expected = {
            # 20 -> 21 (2026-07-27): the apply handler now terminalises its
            # own job before handing off to the first step, because the
            # parent and the child compute a byte-identical
            # `operation_scope_key` and the parent has to release it first.
            # The elevation is the same one the dispatcher applies to the
            # same field on the same record one frame later
            # (`_invoke_handler`'s own `job.sudo().write({'state':
            # 'succeeded'})`), on a job the dispatcher has already claimed
            # and admitted -- it is a state write on connector-owned
            # bookkeeping, reachable only from inside a claimed dispatch,
            # and it exposes no new operator-facing surface. Authorisation
            # and company access were established upstream at enqueue
            # (`enqueue_preview` / `action_confirm_export_preview`).
            'shopify_connector_product_export_service.py': 21,
            'shopify_connector_media_export_service.py': 20,
            'shopify_connector_product_export_preview.py': 2,
            'shopify_connector_product_export_seams.py': 1,
            'shopify_connector_product_media_binding.py': 0,
            'shopify_connector_product_export_wizards.py': 0,
            # U3: the export preview projection reads as the CURRENT user on
            # purpose, so the ordinary ACL and the SEC-3 company record rules
            # apply to it. A budget above zero here would mean the read
            # surface had acquired an elevation, which is exactly the thing
            # this inventory exists to make impossible to add quietly.
            'shopify_connector_product_export_ui.py': 0,
            '__init__.py': 0,
            '__manifest__.py': 0,
        }
        actual = {}
        for path in _python_sources():
            source = path.read_text()
            actual[path.name] = source.count('.sudo(')
        for name, count in actual.items():
            with self.subTest(file=name):
                self.assertIn(
                    name, expected,
                    'a new module file needs a sudo() budget entry',
                )
                self.assertEqual(
                    count, expected[name],
                    'the sudo() count changed in %s: review each elevation '
                    'and update the inventory deliberately' % name,
                )

    # ------------------------------------------------------------------
    # The API version is never hard-coded away from the constant
    # ------------------------------------------------------------------

    def test_no_module_file_hard_codes_an_api_version(self):
        """The version lives in exactly one place.

        A second literal is how a request ends up addressed at a schema
        nobody verified.
        """
        offenders = []
        for path in _python_sources():
            source = path.read_text()
            for token in ('/admin/api/', "'2025-", "'2026-", '"2026-'):
                if token in source:
                    offenders.append((path.name, token))
        self.assertEqual(offenders, [])

    # ------------------------------------------------------------------
    # Test-phase contract (issues #193 / #157)
    # ------------------------------------------------------------------

    def test_every_test_class_declares_its_phase(self):
        """Every connector test class carries `post_install`/`-at_install`.

        Odoo 19 unions `tagged` arguments onto the inherited default
        `{'standard', 'at_install'}`, so omitting `-at_install` leaves a class
        carrying both phases; and an `at_install` class whose fixtures touch a
        table another module extends with a required column fails only on the
        warm update, which is exactly the #193 family.
        """
        offenders = []
        for path in sorted((MODULE_ROOT / 'tests').rglob('test_*.py')):
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                tags = set()
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    for argument in decorator.args:
                        if isinstance(argument, ast.Constant):
                            tags.add(argument.value)
                if not {'post_install'} <= tags or '-at_install' not in tags:
                    offenders.append((path.name, node.name, sorted(tags)))
        self.assertEqual(offenders, [])
