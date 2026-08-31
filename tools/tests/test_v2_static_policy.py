import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "v2_static_policy.py"
SPEC = importlib.util.spec_from_file_location("v2_static_policy_under_test", SCRIPT)
POLICY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = POLICY
SPEC.loader.exec_module(POLICY)


MANIFEST = """{
    'name': 'Static policy fixture',
    'version': '1.0',
    'depends': ['base'],
    'data': ['views/main.xml', 'security/ir.model.access.csv'],
    'assets': {'web.assets_backend': ['demo/static/**/*.js']},
}
"""
ACL = (
    "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
    "access_demo,demo,model_demo,base.group_user,1,0,0,0\n"
)


class StaticPolicyFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write("addons/demo/__manifest__.py", MANIFEST)
        self._write("addons/demo/__init__.py", "from . import tests\n")
        self._write("addons/demo/views/main.xml", "<odoo><data /></odoo>\n")
        self._write("addons/demo/security/ir.model.access.csv", ACL)
        self._write("addons/demo/static/src/demo.js", "export const demo = true;\n")
        self._write("addons/demo/tests/__init__.py", "from . import test_smoke\n")
        self._write("addons/demo/tests/test_smoke.py", "def test_smoke():\n    pass\n")
        # This is an intentional out-of-band helper, not an Odoo test module.
        self._write(
            "addons/demo/tests/runtime_harness.py",
            "def run():\n    return True\n",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _violations(self):
        return POLICY.check_repository(self.root)

    def test_passing_fixture_includes_glob_and_out_of_band_script(self):
        self.assertEqual(self._violations(), [])

    def test_missing_asset_glob_is_reported(self):
        self._write(
            "addons/demo/__manifest__.py",
            MANIFEST.replace("demo/static/**/*.js", "demo/static/missing/*.js"),
        )
        violations = self._violations()
        self.assertTrue(any(
            item.rule == "manifest-reference"
            and "matched no local files" in item.message
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_malformed_xml_is_reported_with_line(self):
        self._write("addons/demo/views/main.xml", "<odoo>\n  <data>\n</odoo>\n")
        violations = self._violations()
        self.assertTrue(any(
            item.path == "addons/demo/views/main.xml"
            and item.rule == "xml-syntax"
            and item.line == 3
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_malformed_csv_is_reported(self):
        self._write(
            "addons/demo/security/ir.model.access.csv",
            ACL.splitlines()[0] + "\n\"unterminated\n",
        )
        violations = self._violations()
        self.assertTrue(any(
            item.path == "addons/demo/security/ir.model.access.csv"
            and item.rule == "csv-syntax"
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_csv_rows_must_match_header(self):
        self._write(
            "addons/demo/security/ir.model.access.csv",
            ACL.splitlines()[0] + "\nshort,row\n",
        )
        violations = self._violations()
        self.assertTrue(any(item.rule == "csv-shape" for item in violations))

    def test_acl_header_requires_all_columns(self):
        self._write(
            "addons/demo/security/ir.model.access.csv",
            "id,name,model_id:id\n1,demo,model_demo\n",
        )
        violations = self._violations()
        self.assertTrue(any(item.rule == "acl-header" for item in violations))

    def test_undiscovered_test_is_reported(self):
        self._write(
            "addons/demo/tests/test_orphan.py",
            "def test_orphan():\n    pass\n",
        )
        violations = self._violations()
        self.assertTrue(any(
            item.path == "addons/demo/tests/test_orphan.py"
            and item.rule == "test-discovery"
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_unresolved_module_global_is_reported(self):
        self._write(
            "addons/demo/models.py",
            "def execute():\n    return missing_dependency.call()\n",
        )
        violations = self._violations()
        self.assertTrue(any(
            item.path == "addons/demo/models.py"
            and item.rule == "python-unresolved-global"
            and "missing_dependency" in item.message
            and item.line == 2
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_closure_and_class_attributes_are_not_reported_as_globals(self):
        self._write(
            "addons/demo/models.py",
            "def outer(value):\n"
            "    class Record:\n"
            "        field = value\n"
            "        def read(self):\n"
            "            return self.field\n"
            "    return Record\n",
        )
        self.assertEqual(self._violations(), [])

    def test_manifest_must_be_literal(self):
        self._write(
            "addons/demo/__manifest__.py",
            "name = 'not literal'\n{'name': name}\n",
        )
        violations = self._violations()
        self.assertTrue(any(item.rule == "manifest-literal" for item in violations))

    def test_duplicate_technical_addon_identity_is_reported(self):
        self._write(
            "addons/nested/demo/__manifest__.py",
            "{'name': 'Nested demo', 'version': '1.0', 'data': []}\n",
        )
        violations = self._violations()
        self.assertTrue(any(
            item.rule == "duplicate-addon-identity"
            and "'demo'" in item.message
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_duplicate_xml_external_id_is_reported(self):
        self._write(
            "addons/demo/__manifest__.py",
            MANIFEST.replace(
                "'views/main.xml',",
                "'views/main.xml', 'views/duplicate.xml',",
            ),
        )
        self._write(
            "addons/demo/views/main.xml",
            "<odoo>\n  <record id='demo_record' model='demo.model' />\n</odoo>\n",
        )
        self._write(
            "addons/demo/views/duplicate.xml",
            "<odoo>\n  <record id='demo_record' model='demo.model' />\n</odoo>\n",
        )
        violations = self._violations()
        self.assertTrue(any(
            item.rule == "xml-duplicate-id"
            and "demo_record" in item.message
            and item.line == 2
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_duplicate_acl_external_id_is_reported(self):
        self._write(
            "addons/demo/__manifest__.py",
            MANIFEST.replace(
                "'security/ir.model.access.csv'",
                "'security/ir.model.access.csv', "
                "'security/extra.access.csv'",
            ),
        )
        self._write("addons/demo/security/extra.access.csv", ACL)
        violations = self._violations()
        self.assertTrue(any(
            item.rule == "acl-duplicate-id"
            and "access_demo" in item.message
            for item in violations
        ), "\n".join(item.format() for item in violations))

    def test_cli_accepts_repo_root_without_odoo(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("v2 static policy: pass", result.stdout)


class TestRealRepository(unittest.TestCase):
    def test_real_repository_passes(self):
        root = SCRIPT.parents[1]
        violations = POLICY.check_repository(root)
        self.assertEqual(
            [], violations, "\n".join(item.format() for item in violations)
        )


if __name__ == "__main__":
    unittest.main()
