"""U1 acceptance A20 -- package import structure.

The addon ROOT package is the only place the `wizards` package is registered.
`models/__init__.py` must never import its sibling `wizards` package: that
creates a second registration path for the same modules, which in Odoo shows up
as duplicate model registration or an import cycle rather than as a clean error.
"""

import ast
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


def _imported_names(source):
    """Every module name reached by `from . import X` in this source."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            for alias in node.names:
                names.append(alias.name)
    return names


@tagged('post_install', '-at_install')
class TestUiImportStructure(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[1]

    def test_root_init_imports_wizards_exactly_once(self):
        names = _imported_names(
            (self._addon_root() / '__init__.py').read_text(encoding='utf-8')
        )
        self.assertEqual(
            names.count('wizards'), 1,
            'The addon root __init__.py must import `wizards` exactly once; '
            'found %d occurrence(s) in %s' % (names.count('wizards'), names),
        )
        self.assertIn('models', names, 'The root must still import `models`.')

    def test_models_init_does_not_import_the_wizards_package(self):
        names = _imported_names(
            (self._addon_root() / 'models' / '__init__.py').read_text(encoding='utf-8')
        )
        self.assertNotIn(
            'wizards', names,
            'models/__init__.py must NOT import the sibling wizards package -- '
            'the addon root is the only registration point.',
        )

    def test_wizards_init_imports_each_module_exactly_once(self):
        names = _imported_names(
            (self._addon_root() / 'wizards' / '__init__.py').read_text(encoding='utf-8')
        )
        self.assertEqual(
            sorted(names), sorted(set(names)),
            'wizards/__init__.py imports a module more than once: %s' % names,
        )
        on_disk = sorted(
            p.stem for p in (self._addon_root() / 'wizards').glob('*.py')
            if p.stem != '__init__'
        )
        self.assertEqual(
            sorted(names), on_disk,
            'Every wizard module on disk must be imported exactly once, and no '
            'import may name a module that does not exist.',
        )

    def test_wizard_models_are_registered_after_install(self):
        """The registry is the real proof that the import path worked."""
        for model_name in (
            'shopify.connector.fulfillment.mode.switch.wizard',
            'shopify.connector.fulfillment.review.release.wizard',
        ):
            self.assertIn(
                model_name, self.env,
                'Wizard model %s is not in the registry -- the wizards package '
                'was not loaded.' % model_name,
            )
            self.assertTrue(
                self.env[model_name]._transient,
                '%s must be a TransientModel.' % model_name,
            )

    def test_no_wizard_module_is_imported_from_models(self):
        """No models/*.py may reach into the wizards package by any path."""
        offenders = []
        for path in (self._addon_root() / 'models').glob('*.py'):
            source = path.read_text(encoding='utf-8')
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if 'wizards' in node.module.split('.'):
                        offenders.append(path.name)
        self.assertFalse(offenders, 'models/ imports wizards in: %s' % offenders)
