"""Focused static checks for the DEC-029 Odoo Apps packaging contract."""

import ast
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_shopify_connector_bundle.py"
SPEC = importlib.util.spec_from_file_location("shopify_connector_packaging_audit", SCRIPT)
PACKAGING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGING)


class TestShopifyConnectorPackagingAudit(unittest.TestCase):
    def test_all_dec029_manifests_use_odoo19_release_metadata(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            for module_name in PACKAGING.EDITION_MODULES[edition]:
                manifest_path = ROOT / "addons" / module_name / "__manifest__.py"
                tree = ast.parse(
                    manifest_path.read_text(encoding="utf-8"), str(manifest_path)
                )
                manifest = ast.literal_eval(tree.body[0].value)
                with self.subTest(edition=edition, module=module_name):
                    self.assertIsInstance(manifest, dict)
                    self.assertTrue(manifest.get("name"))
                    self.assertRegex(
                        str(manifest.get("version", "")), r"^19\.0(?:\.|$)"
                    )
                    self.assertEqual(manifest.get("license"), "LGPL-3")
                    self.assertIs(manifest.get("installable"), True)
                    self.assertIs(manifest.get("auto_install"), False)

    def test_dec029_sets_are_explicit_and_nested(self):
        self.assertEqual(
            PACKAGING.EDITION_COMPANION_MODULES["lite"],
            (
                "shopify_connector_core",
                "shopify_connector_product",
                "shopify_connector_sale",
            ),
        )
        self.assertEqual(
            PACKAGING.EDITION_COMPANION_MODULES["full"][:3],
            PACKAGING.EDITION_COMPANION_MODULES["lite"],
        )
        self.assertEqual(
            PACKAGING.EDITION_COMPANION_MODULES["full"][3:],
            (
                "shopify_connector_inventory",
                "shopify_connector_fulfillment",
                "shopify_connector_product_export",
            ),
        )
        self.assertEqual(
            PACKAGING.EDITION_ACCELERATOR_MODULES["lite"],
            (
                "shopify_connector_webhook",
                "shopify_connector_product_webhook",
                "shopify_connector_sale_webhook",
            ),
        )
        self.assertEqual(
            PACKAGING.EDITION_ACCELERATOR_MODULES["full"][3:],
            (
                "shopify_connector_inventory_webhook",
                "shopify_connector_fulfillment_webhook",
            ),
        )
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            self.assertEqual(
                tuple(
                    PACKAGING._read_manifest(
                        ROOT / "addons" / PACKAGING.EDITION_META_MODULES[edition]
                    ).get("depends", ())
                ),
                PACKAGING.EDITION_META_DEPENDENCIES[edition],
            )
        self.assertNotIn(PACKAGING.LEGACY_META_MODULE, PACKAGING.EDITION_MODULES["lite"])
        self.assertNotIn(PACKAGING.LEGACY_META_MODULE, PACKAGING.EDITION_MODULES["full"])

    def test_legacy_suite_is_not_an_odoo_addon_candidate(self):
        """The branch-introduced all-family convenience tree has no manifest."""

        legacy = ROOT / "addons" / PACKAGING.LEGACY_META_MODULE
        self.assertFalse(
            (legacy / "__manifest__.py").exists(),
            "the historical all-family tree must not be discoverable as an Odoo app",
        )

    def test_declared_manifest_files_exist(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            for module_name in PACKAGING.EDITION_MODULES[edition]:
                module_path = ROOT / "addons" / module_name
                manifest = PACKAGING._read_manifest(module_path)
                for key in ("data", "demo", "images"):
                    for relative_path in manifest.get(key) or ():
                        with self.subTest(
                            edition=edition,
                            module=module_name,
                            field=key,
                            path=relative_path,
                        ):
                            self.assertTrue((module_path / relative_path).is_file())
                for bundle, asset_paths in (manifest.get("assets") or {}).items():
                    for asset_path in asset_paths:
                        with self.subTest(
                            edition=edition,
                            module=module_name,
                            bundle=bundle,
                            path=asset_path,
                        ):
                            self.assertTrue((ROOT / "addons" / asset_path).is_file())

    def test_archive_has_flat_known_edition_roots_and_no_inert_sources(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            with tempfile.TemporaryDirectory() as temporary:
                archive_path = Path(temporary) / f"{edition}.zip"
                PACKAGING.build_bundle(archive_path, edition)
                with zipfile.ZipFile(archive_path) as archive:
                    names = archive.namelist()
                self.assertEqual(
                    {name.split("/", 1)[0] for name in names},
                    set(PACKAGING.EDITION_MODULES[edition]) | {"LICENSE"},
                )
                self.assertTrue(all(".." not in Path(name).parts for name in names))
                self.assertFalse(any("/static/src/p16/" in f"/{name}" for name in names))
                self.assertFalse(any("/static/src/v2/" in f"/{name}" for name in names))
                self.assertFalse(
                    any(
                        name.endswith(
                            "shopify_connector_core/views/shopify_connector_p16_admin_views.xml"
                        )
                        for name in names
                    )
                )
                if edition == "lite":
                    self.assertFalse(
                        any(
                            name.startswith(
                                (
                                    "shopify_connector_inventory/",
                                    "shopify_connector_fulfillment/",
                                    "shopify_connector_product_export/",
                                )
                            )
                            for name in names
                        )
                    )

    def test_symlinked_source_is_rejected_before_archive_read(self):
        module_path = ROOT / "addons" / PACKAGING.EDITION_META_MODULES["lite"]
        with tempfile.NamedTemporaryFile() as outside:
            link = module_path / "_packaging_audit_external_link.txt"
            link.symlink_to(outside.name)
            try:
                with self.assertRaises(PACKAGING.PackageValidationError):
                    tuple(PACKAGING._iter_module_files(PACKAGING.EDITION_META_MODULES["lite"]))
            finally:
                link.unlink(missing_ok=True)

    def test_symlinked_addon_root_is_rejected(self):
        original_addons_root = PACKAGING.ADDONS_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            temporary_addons = Path(temporary) / "addons"
            temporary_addons.mkdir()
            link = temporary_addons / PACKAGING.EDITION_META_MODULES["lite"]
            link.symlink_to(
                ROOT / "addons" / PACKAGING.EDITION_META_MODULES["lite"],
                target_is_directory=True,
            )
            PACKAGING.ADDONS_ROOT = temporary_addons
            try:
                with self.assertRaises(PACKAGING.PackageValidationError):
                    tuple(
                        PACKAGING._iter_module_files(
                            PACKAGING.EDITION_META_MODULES["lite"]
                        )
                    )
            finally:
                PACKAGING.ADDONS_ROOT = original_addons_root

    def test_dependencies_are_closed_over_each_edition_or_odoo_builtin(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            available = set(PACKAGING.EDITION_MODULES[edition])
            for module_name in PACKAGING.EDITION_MODULES[edition]:
                manifest = PACKAGING._read_manifest(ROOT / "addons" / module_name)
                for dependency in manifest.get("depends", ()):
                    with self.subTest(
                        edition=edition, module=module_name, dependency=dependency
                    ):
                        self.assertIn(
                            dependency,
                            available | PACKAGING.ODOO_BUILTIN_DEPENDENCIES,
                        )

    def test_core_has_no_stale_graphql_external_dependency_or_import(self):
        core_manifest = PACKAGING._read_manifest(
            ROOT / "addons" / "shopify_connector_core"
        )
        self.assertNotIn("external_dependencies", core_manifest)
        import_pattern = re.compile(r"(?m)^\s*(?:from|import)\s+graphql(?:\s|\.|$)")
        for path in (ROOT / "addons").rglob("*.py"):
            if "tests" in path.parts:
                continue
            with self.subTest(path=path):
                self.assertIsNone(import_pattern.search(path.read_text(encoding="utf-8")))

    def test_presentation_discloses_fixture_and_scope_boundary(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            module_path = ROOT / "addons" / PACKAGING.EDITION_META_MODULES[edition]
            manifest = PACKAGING._read_manifest(module_path)
            description = (
                (module_path / "static" / "description" / "index.html").read_text(
                    encoding="utf-8"
                )
                + "\n"
                + str(manifest.get("description", ""))
            ).lower()
            with self.subTest(edition=edition):
                for marker in (
                    "synthetic fixtures",
                    "not odoo.sh/uat",
                    "future domains",
                    "webhook",
                    "event",
                ):
                    self.assertIn(marker, description)
                for forbidden in (
                    "oauth",
                    "real-time",
                    "real time",
                ):
                    self.assertNotIn(forbidden, description)
                self.assertNotIn("https://", description)
                if edition == "lite":
                    for unavailable in (
                        "inventory",
                        "fulfillment",
                        "product export",
                        "product_export",
                    ):
                        self.assertNotIn(unavailable, description)
                    self.assertEqual(
                        PACKAGING._read_manifest(module_path).get("images"), []
                    )
                    self.assertFalse(
                        (module_path / "images").exists(),
                        "Lite must not carry Full-only listing screenshots",
                    )

    def test_audit_evidence_records_edition_and_remaining_gates(self):
        audit = (
            ROOT
            / "docs"
            / "v2"
            / "evidence"
            / "odoo-apps-packaging-audit-2026-08-30.md"
        ).read_text(encoding="utf-8").lower()
        for marker in (
            "dec-029",
            "shopify_connector_lite",
            "shopify_connector_full",
            "pkg-03",
            "pkg-04",
            "pkg-05",
            "no production `import graphql`",
            "migration module set",
        ):
            self.assertIn(marker, audit)

    def test_runner_keeps_meta_install_out_of_old_tree_migrations(self):
        runner = (ROOT / "tools" / "run_connector_suite.sh").read_text(encoding="utf-8")
        self.assertIn('META_MODULES="shopify_connector_lite,shopify_connector_full"', runner)
        self.assertIn('MIGRATION_MODULES="$MODULES"', runner)
        migration_start = runner.index("# --- Pass 2b: genuine version-to-version migrations")
        migration_end = runner.index("# --- Pass 3: the non-standard tag suite")
        migration_block = runner[migration_start:migration_end]
        self.assertNotIn("META_MODULES", migration_block)
        self.assertNotIn("shopify_connector_lite", migration_block)
        self.assertNotIn("shopify_connector_full", migration_block)

    def test_upgrade_runbook_versions_match_current_connector_manifests(self):
        """Keep the operator upgrade command aligned with this candidate."""

        runbook = (ROOT / "docs" / "runbooks" / "upgrade-and-rollback.md").read_text(
            encoding="utf-8"
        )
        version_line = next(
            (
                line
                for line in runbook.splitlines()
                if "For this V2 candidate the versions are" in line
            ),
            "",
        )
        self.assertTrue(version_line, "upgrade runbook has no current-version inventory")
        labels = {
            "core": "shopify_connector_core",
            "product": "shopify_connector_product",
            "sale": "shopify_connector_sale",
            "inventory": "shopify_connector_inventory",
            "fulfillment": "shopify_connector_fulfillment",
            "product export": "shopify_connector_product_export",
            "webhook": "shopify_connector_webhook",
            "product webhook": "shopify_connector_product_webhook",
            "inventory webhook": "shopify_connector_inventory_webhook",
            "sale webhook": "shopify_connector_sale_webhook",
            "fulfillment webhook": "shopify_connector_fulfillment_webhook",
        }
        for label, module_name in labels.items():
            manifest = PACKAGING._read_manifest(ROOT / "addons" / module_name)
            with self.subTest(module=module_name):
                self.assertIn(
                    f"{label} `{manifest['version']}`",
                    version_line,
                    f"upgrade runbook version for {module_name} is stale",
                )


if __name__ == "__main__":
    unittest.main()
