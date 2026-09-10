import ast
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'perf0_baseline.py'
SPEC = importlib.util.spec_from_file_location('perf0_baseline_under_test', SCRIPT)
PERF0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PERF0)


class TestPerf0DatasetScale(unittest.TestCase):
    def test_default_and_positive_scale_multiply_only_dataset_rows(self):
        self.assertEqual(PERF0.scaled_dataset_rows(50, 1), 50)
        self.assertEqual(PERF0.scaled_dataset_rows(50, 3), 150)
        self.assertEqual(PERF0.scaled_dataset_rows(0, 25), 0)

    def test_scale_rejects_invalid_values(self):
        for value in (0, -1, True, False, 1.5, '2'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'scale'):
                    PERF0.scaled_dataset_rows(50, value)

    def test_scale_rejects_unsafe_dataset_size(self):
        maximum = PERF0.MAX_DATASET_ROWS
        self.assertEqual(PERF0.scaled_dataset_rows(maximum, 1), maximum)
        with self.assertRaisesRegex(ValueError, 'safety limit'):
            PERF0.scaled_dataset_rows(maximum, 2)
        with self.assertRaisesRegex(ValueError, 'safety limit'):
            PERF0.scaled_dataset_rows(1, maximum + 1)

    def test_base_rows_reject_invalid_values(self):
        for value in (-1, True, False, 1.5, '50'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'base dataset rows'):
                    PERF0.scaled_dataset_rows(value, 1)

    def test_fixture_validates_scale_without_odoo(self):
        self.assertEqual(PERF0.Fixture(None, 1).scale, 1)
        self.assertEqual(PERF0.Fixture(None, 4).scale, 4)
        with self.assertRaisesRegex(ValueError, 'greater than zero'):
            PERF0.Fixture(None, 0)

    def test_every_domain_seed_call_uses_the_helper(self):
        tree = ast.parse(SCRIPT.read_text(encoding='utf-8'))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'build_domain_dataset'
        ]
        self.assertEqual(len(calls), 7)
        for call in calls:
            self.assertEqual(len(call.args), 1)
            argument = call.args[0]
            self.assertIsInstance(argument, ast.Call)
            self.assertIsInstance(argument.func, ast.Name)
            self.assertEqual(argument.func.id, 'scaled_dataset_rows')


if __name__ == '__main__':
    unittest.main()
