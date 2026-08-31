import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "v2_change_size_policy.py"
SPEC = importlib.util.spec_from_file_location("v2_change_size_policy_tested", SCRIPT)
POLICY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = POLICY
SPEC.loader.exec_module(POLICY)


class ChangeSizePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "policy@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Policy Test"],
            cwd=self.root,
            check=True,
        )
        self._write("addons/demo/models/small.py", "x = 1\n")
        self._write("addons/demo/models/hotspot.py", "x\n" * 800)
        self._write("addons/demo/tests/test_large.py", "x\n" * 900)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)
        self.base = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True,
        ).strip()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_new_production_file_over_ceiling_fails(self):
        self._write("addons/demo/models/new.py", "x\n" * 751)
        violations = POLICY.check_change_sizes(self.root, self.base)
        self.assertEqual([item.path for item in violations], [
            "addons/demo/models/new.py",
        ])

    def test_existing_hotspot_may_shrink_but_not_grow(self):
        self._write("addons/demo/models/hotspot.py", "x\n" * 799)
        self.assertEqual(POLICY.check_change_sizes(self.root, self.base), [])
        self._write("addons/demo/models/hotspot.py", "x\n" * 801)
        violations = POLICY.check_change_sizes(self.root, self.base)
        self.assertEqual(len(violations), 1)
        self.assertIn("may not grow", violations[0].message)

    def test_tests_and_migrations_are_excluded(self):
        self._write("addons/demo/tests/test_large.py", "x\n" * 1200)
        self._write("addons/demo/migrations/1.1/post-migrate.py", "x\n" * 900)
        self.assertEqual(POLICY.check_change_sizes(self.root, self.base), [])

    def test_invalid_or_missing_base_fails_closed(self):
        with self.assertRaises(ValueError):
            POLICY.check_change_sizes(self.root, "HEAD")
        with self.assertRaises(ValueError):
            POLICY.check_change_sizes(self.root, "0" * 40)


if __name__ == "__main__":
    unittest.main()
