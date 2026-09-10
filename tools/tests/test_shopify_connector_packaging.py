import hashlib
import fnmatch
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_shopify_connector_bundle.py"
SPEC = importlib.util.spec_from_file_location("shopify_connector_packaging", SCRIPT)
PACKAGING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGING)


class TestShopifyConnectorPackaging(unittest.TestCase):
    def test_source_tree_is_valid_for_both_dec029_editions(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            with self.subTest(edition=edition):
                files = PACKAGING.validate_source_tree(edition)
                self.assertIn(PACKAGING.LICENSE_PATH, files)
                meta = PACKAGING._read_manifest(
                    ROOT / "addons" / PACKAGING.EDITION_META_MODULES[edition]
                )
                self.assertEqual(
                    list(meta["depends"]),
                    list(PACKAGING.EDITION_META_DEPENDENCIES[edition]),
                )
                self.assertEqual(
                    set(PACKAGING.EDITION_ACCELERATOR_MODULES[edition]),
                    set(PACKAGING.EDITION_MODULES[edition])
                    - {PACKAGING.EDITION_META_MODULES[edition]}
                    - set(PACKAGING.EDITION_COMPANION_MODULES[edition]),
                )

    def test_screenshots_are_exact_evidence_copies(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            for target, source in PACKAGING.EDITION_IMAGE_SOURCES[edition].items():
                target_path = (
                    ROOT
                    / "addons"
                    / PACKAGING.EDITION_META_MODULES[edition]
                    / target
                )
                source_path = ROOT / source
                with self.subTest(edition=edition, target=target):
                    self.assertEqual(
                        hashlib.sha256(target_path.read_bytes()).digest(),
                        hashlib.sha256(source_path.read_bytes()).digest(),
                    )

    def test_screenshots_are_rendered_odoo_browser_evidence(self):
        evidence_root = ROOT / PACKAGING.BROWSER_EVIDENCE_ROOT
        for target, source in PACKAGING.EDITION_IMAGE_SOURCES["full"].items():
            source_path = ROOT / source
            with self.subTest(target=target):
                self.assertTrue(source_path.is_relative_to(evidence_root), source)
                self.assertNotIn("09-ui-prototype", source)
                self.assertNotIn("prototype", source.lower())
                PACKAGING._validate_browser_evidence_source(source)
                header = source_path.read_bytes()[:24]
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                self.assertIn(width, {1366, 1440})
                self.assertEqual(height, 900)

    def test_prototype_only_sources_are_rejected(self):
        with self.assertRaises(PACKAGING.PackageValidationError):
            PACKAGING._validate_browser_evidence_source(
                "docs/09-ui-prototype/review-evidence/desktop/dashboard.png"
            )

    def test_listing_discloses_scope_and_evidence_boundary(self):
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
                self.assertIn("synthetic fixtures", description)
                self.assertIn("not odoo.sh/uat", description)
                self.assertIn("future domains", description)
                self.assertIn("webhook", description)
                self.assertIn("event", description)
                self.assertNotIn("real-time", description)
                self.assertNotIn("real time", description)
                self.assertNotIn("oauth", description)
                if edition == "full":
                    self.assertIn("up to ten", description)
                    self.assertIn("per odoo database", description)
                    self.assertIn("bounded support limit", description)
                    self.assertNotIn("multi-store are not included", description)

    def test_bundle_is_deterministic_and_excludes_development_material(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            with tempfile.TemporaryDirectory() as temporary:
                first = Path(temporary) / f"{edition}-first.zip"
                second = Path(temporary) / f"{edition}-second.zip"
                PACKAGING.build_bundle(first, edition)
                PACKAGING.build_bundle(second, edition)
                self.assertEqual(first.read_bytes(), second.read_bytes())

                with zipfile.ZipFile(first) as archive:
                    names = archive.namelist()
                top_level = {name.split("/", 1)[0] for name in names}
                self.assertEqual(
                    top_level,
                    set(PACKAGING.EDITION_MODULES[edition]) | {"LICENSE"},
                )
                self.assertIn("LICENSE", names)
                self.assertTrue(
                    any(name.endswith("/static/description/index.html") for name in names)
                )
                self.assertTrue(
                    any(name.endswith("/static/description/icon.png") for name in names)
                )
                self.assertFalse(
                    any(
                        len(Path(name).parts) > 1
                        and Path(name).parts[0] in PACKAGING.EDITION_MODULES[edition]
                        and Path(name).parts[1] == "tests"
                        for name in names
                    )
                )
                self.assertFalse(any(name.endswith("README.md") for name in names))
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any(name.startswith("docs/") for name in names))
                for accelerator in PACKAGING.EDITION_ACCELERATOR_MODULES[edition]:
                    self.assertTrue(
                        any(name.startswith(f"{accelerator}/") for name in names),
                        accelerator,
                    )
                if edition == "lite":
                    self.assertFalse(
                        any(name.startswith("shopify_connector_lite/images/") for name in names)
                    )

    def test_extracted_archive_has_install_and_manifest_closure(self):
        """Validate the archive itself, not only the checkout that produced it."""

        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            with tempfile.TemporaryDirectory() as temporary:
                temporary_path = Path(temporary)
                archive_path = temporary_path / f"{edition}.zip"
                PACKAGING.build_bundle(archive_path, edition)
                extracted = temporary_path / "extracted"
                extracted.mkdir()
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(extracted)
                    archive_names = set(archive.namelist())

                self.assertIn("LICENSE", archive_names)
                available = set(PACKAGING.EDITION_MODULES[edition])
                for module_name in PACKAGING.EDITION_MODULES[edition]:
                    module_path = extracted / module_name
                    self.assertTrue(
                        module_path.is_dir(),
                        f"{edition}: missing extracted addon {module_name}",
                    )
                    manifest = PACKAGING._read_manifest(module_path)
                    self.assertTrue(manifest.get("installable"), module_name)
                    for dependency in manifest.get("depends", ()):
                        self.assertIn(
                            dependency,
                            available | PACKAGING.ODOO_BUILTIN_DEPENDENCIES,
                            f"{edition}: unresolved dependency {dependency}",
                        )
                    for reference in PACKAGING._manifest_archive_references(
                        module_name, manifest
                    ):
                        self.assertTrue(
                            any(
                                fnmatch.fnmatchcase(name, reference)
                                for name in archive_names
                            ),
                            f"{edition}: missing extracted manifest target {reference}",
                        )

                # The archive helper repeats this check against the ZIP
                # members so a future test cannot accidentally validate only
                # the extracted filesystem's symlink-resolved view.
                self.assertEqual(
                    set(PACKAGING.validate_archive_manifest_closure(archive_path, edition)),
                    archive_names,
                )

    def test_manifest_declared_test_assets_are_retained_in_test_mode(self):
        """Unit assets and browser tours remain available after packaging."""

        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            with tempfile.TemporaryDirectory() as temporary:
                archive_path = Path(temporary) / f"{edition}.zip"
                PACKAGING.build_bundle(archive_path, edition)
                with zipfile.ZipFile(archive_path) as archive:
                    names = set(archive.namelist())
                for module_name in PACKAGING.EDITION_MODULES[edition]:
                    manifest = PACKAGING._read_manifest(ROOT / "addons" / module_name)
                    assets = manifest.get("assets") or {}
                    for bundle_name in ("web.assets_tests", "web.assets_unit_tests"):
                        for reference in assets.get(bundle_name, ()):
                            if isinstance(reference, str):
                                with self.subTest(
                                    edition=edition,
                                    module=module_name,
                                    bundle=bundle_name,
                                    reference=reference,
                                ):
                                    self.assertIn(reference, names)

    def test_output_paths_inside_checkout_and_non_zip_suffixes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary)
            with self.assertRaises(PACKAGING.PackageValidationError):
                PACKAGING.build_bundle(ROOT / "packaging-audit-output.zip", "lite")
            with self.assertRaises(PACKAGING.PackageValidationError):
                PACKAGING.build_bundle(
                    ROOT / "addons" / "shopify_connector_core" / "nested.zip",
                    "lite",
                )
            with self.assertRaises(PACKAGING.PackageValidationError):
                PACKAGING.build_bundle(outside / "lite.tar", "lite")

    def test_symlinked_license_and_evidence_source_are_rejected(self):
        original_root = PACKAGING.REPO_ROOT
        original_addons = PACKAGING.ADDONS_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            (temporary_root / "addons").mkdir()
            (temporary_root / "LICENSE").symlink_to(ROOT / "LICENSE")
            PACKAGING.REPO_ROOT = temporary_root
            PACKAGING.ADDONS_ROOT = temporary_root / "addons"
            with self.assertRaises(PACKAGING.PackageValidationError):
                PACKAGING._validate_license()
        PACKAGING.REPO_ROOT = original_root
        PACKAGING.ADDONS_ROOT = original_addons

        source = ROOT / PACKAGING.EDITION_IMAGE_SOURCES["full"][
            "images/dashboard_screenshot.png"
        ]
        link = source.with_name("_packaging_audit_symlink.png")
        link.symlink_to(source)
        try:
            with self.assertRaises(PACKAGING.PackageValidationError):
                PACKAGING._validate_browser_evidence_source(
                    str(link.relative_to(ROOT)).replace("\\", "/")
                )
        finally:
            link.unlink(missing_ok=True)

    def test_generated_meta_module_bytecode_does_not_break_validation(self):
        for edition in PACKAGING.MARKETPLACE_EDITIONS:
            meta_module = PACKAGING.EDITION_META_MODULES[edition]
            cache_dir = ROOT / "addons" / meta_module / "__pycache__"
            cache_dir.mkdir(exist_ok=True)
            generated = cache_dir / "generated.cpython-test.pyc"
            generated.write_bytes(b"generated-test-bytecode")
            try:
                files = PACKAGING.validate_source_tree(edition)
                self.assertFalse(any("__pycache__" in path.parts for path in files))
                self.assertFalse(any(path.suffix == ".pyc" for path in files))
            finally:
                generated.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
