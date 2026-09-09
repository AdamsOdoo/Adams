"""Focused native selection must include explicitly inventoried race classes."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import run_connector_focus as focus


class TestConnectorFocusSelection(unittest.TestCase):
    def test_inventory_selects_exact_classes_without_implicit_standard_tag(self):
        config = json.loads(focus.CONFIG.read_text())
        selectors, names = focus.selected_classes(config)
        self.assertEqual(len(selectors), 48)
        self.assertEqual(names, [item['class'] for item in config['classes']])
        # Pinned Odoo tag_selector.py defaults an omitted positive tag to
        # 'standard', while '*' removes the tag filter and retains module/class.
        self.assertEqual(selectors, [
            f"*/{item['addon']}:{item['class']}" for item in config['classes']
        ])
        self.assertIn('*/shopify_connector_product:TestProductRuntimePerformance', selectors)
        self.assertIn('*/shopify_connector_sale:TestCustomerMatchingConcurrency', selectors)

    def test_invalid_or_broadening_inventory_entries_fail_closed(self):
        for item in (
            {'addon': 'shopify_connector_core,*', 'class': 'TestOne'},
            {'addon': 'shopify_connector_core', 'class': '*'},
            {'addon': 'shopify_connector_core', 'class': 'TestOne,standard'},
            {'addon': 'shopify_connector_core', 'class': 'TestDefinitelyAbsent'},
        ):
            with self.subTest(item=item), self.assertRaises(RuntimeError):
                focus.selected_classes({'classes': [item]})

    def test_empty_and_duplicate_selection_fail_closed(self):
        item = json.loads(focus.CONFIG.read_text())['classes'][0]
        for classes in ([], [item, item]):
            with self.subTest(classes=classes), self.assertRaises(RuntimeError):
                focus.selected_classes({'classes': classes})

    def test_nonstandard_fixture_requires_no_standard_decorator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'addons/shopify_connector_core/tests'
            tests.mkdir(parents=True)
            (tests / 'test_race.py').write_text(
                "@tagged('-standard', 'post_install', 'race')\n"
                "class TestRace(TransactionCase):\n    pass\n"
            )
            with patch.object(focus, 'ROOT', root):
                selectors, names = focus.selected_classes({'classes': [
                    {'addon': 'shopify_connector_core', 'class': 'TestRace'}
                ]})
            self.assertEqual(selectors, ['*/shopify_connector_core:TestRace'])
            self.assertEqual(names, ['TestRace'])


if __name__ == '__main__':
    unittest.main()
