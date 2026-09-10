#!/usr/bin/env python3
"""Validate and build the DEC-029 Lite/Full distribution bundles.

The repository contains a modular connector family.  Odoo can install the
modules independently, while each marketplace bundle gives an operator one
edition-specific application entry point and one deterministic archive for
distribution.  The builder is deliberately offline: it reads only the
repository and never needs Shopify, Odoo, credentials, or third-party Python
packages.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import os
from pathlib import Path
import re
import sys
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = REPO_ROOT / "addons"
# DEC-029 defines editions by their direct, installable domain modules.  The
# current near-real-time contract also requires the generic webhook foundation
# and the domain satellites in each edition's *installation closure*.  The
# satellites remain separate addons (P20 no-consolidation); listing them here
# makes the closure explicit instead of silently shipping scheduled-only
# editions.
EDITION_META_MODULES = {
    "lite": "shopify_connector_lite",
    "full": "shopify_connector_full",
}
EDITION_COMPANION_MODULES = {
    "lite": (
        "shopify_connector_core",
        "shopify_connector_product",
        "shopify_connector_sale",
    ),
    "full": (
        "shopify_connector_core",
        "shopify_connector_product",
        "shopify_connector_sale",
        "shopify_connector_inventory",
        "shopify_connector_fulfillment",
        "shopify_connector_product_export",
    ),
}
# These modules are required to activate the current webhook-first path for
# each edition.  They are deliberately not folded into their owning domains:
# P20 is optional and requires separate lifecycle/XML-ID proof.
EDITION_ACCELERATOR_MODULES = {
    "lite": (
        "shopify_connector_webhook",
        "shopify_connector_product_webhook",
        "shopify_connector_sale_webhook",
    ),
    "full": (
        "shopify_connector_webhook",
        "shopify_connector_product_webhook",
        "shopify_connector_sale_webhook",
        "shopify_connector_inventory_webhook",
        "shopify_connector_fulfillment_webhook",
    ),
}
EDITION_META_DEPENDENCIES = {
    edition: (*EDITION_COMPANION_MODULES[edition], *accelerators)
    for edition, accelerators in EDITION_ACCELERATOR_MODULES.items()
}
EDITION_MODULES = {
    edition: (
        EDITION_META_MODULES[edition],
        *EDITION_COMPANION_MODULES[edition],
        *EDITION_ACCELERATOR_MODULES[edition],
    )
    for edition in EDITION_COMPANION_MODULES
}
MARKETPLACE_EDITIONS = tuple(EDITION_MODULES)

# Compatibility aliases for callers that previously validated the all-family
# bundle.  They now describe the Full DEC-029 output; no legacy suite archive
# is produced by this builder.
META_MODULE = EDITION_META_MODULES["full"]
COMPANION_MODULES = EDITION_COMPANION_MODULES["full"]
ALL_MODULES = EDITION_MODULES["full"]
LEGACY_META_MODULE = "shopify_connector_suite"
EDITION_DISPLAY_NAMES = {"lite": "Lite", "full": "Full"}
EDITION_MANIFEST_NAMES = {
    "lite": "Shopify Connector Lite",
    "full": "Shopify Connector Full",
}
LICENSE_PATH = Path("LICENSE")
LICENSE_SHA256 = "e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118"
ROOT_DISTRIBUTION_FILES = (LICENSE_PATH,)
ODOO_BUILTIN_DEPENDENCIES = {
    "base",
    "web",
    "product",
    "sale",
    "stock",
    "stock_delivery",
    "sale_stock",
}

# Every image is copied from a durable, rendered Odoo browser-evidence screen.
# The source/target hash check prevents an accidentally edited or invented
# image from silently entering the release archive.  In particular, the
# marketplace package must never fall back to the documentation-only visual
# prototype gallery under docs/09-ui-prototype.
IMAGE_SOURCES = {
    "images/dashboard_screenshot.png": (
        "docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/"
        "u0-dashboard-healthy-desktop-1366px.png"
    ),
    "images/settings_screenshot.png": (
        "docs/05-qa/evidence/u1-browser-2026-07-25/09-admin-settings-form.png"
    ),
    "images/order_review_screenshot.png": (
        "docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/"
        "u2-orders-workspace-empty-desktop-1366px.png"
    ),
    "images/inventory_screenshot.png": (
        "docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/"
        "u2-inventory-workspace-desktop-1366px.png"
    ),
    "images/fulfillment_screenshot.png": (
        "docs/05-qa/evidence/u1-browser-2026-07-25/04-user-fulfillments.png"
    ),
    "images/jobs_screenshot.png": (
        "docs/05-qa/evidence/u1-browser-2026-07-25/05-user-fulfillment-jobs.png"
    ),
}
# The existing captures include Full-only navigation where appropriate.  Lite
# therefore publishes no screenshots until a core/product/sale-only evidence
# set exists; an empty manifest image list is safer than showing an unavailable
# domain in the Lite listing.  Full retains the reviewed six-screen set.
EDITION_IMAGE_SOURCES = {
    "lite": {},
    "full": IMAGE_SOURCES,
}
BROWSER_EVIDENCE_ROOT = Path("docs/05-qa/evidence")
BROWSER_EVIDENCE_README_MARKERS = ("browser", "chromium", "screenshot")

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "dev",
    "docs",
    "fixtures",
    "node_modules",
    "tests",
}
EXCLUDED_SUFFIXES = {
    # Distribution source must contain source files, not nested release
    # artifacts.  In particular, a ZIP created by an earlier packaging pass
    # must never become an input to a later pass.
    ".7z",
    ".bz",
    ".bz2",
    ".cab",
    ".cpio",
    ".egg",
    ".gz",
    ".jar",
    ".lz",
    ".lz4",
    ".key",
    ".log",
    ".pem",
    ".pfx",
    ".pyc",
    ".p12",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tbz",
    ".tbz2",
    ".tgz",
    ".txz",
    ".whl",
    ".xz",
    ".zip",
    ".zst",
}
EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
}
# These presentation trees are deliberately inert until a later V2/P16
# checkpoint wires them into an Odoo asset bundle.  They are source-level
# design/contract artifacts, not part of the current release surface.  Keep
# the paths explicit rather than excluding every future-looking filename: the
# normal production Python/XML/SCSS tree still needs to be packaged in full.
INERT_SOURCE_PATH_PREFIXES = (
    ("addons", "shopify_connector_core", "static", "src", "p16"),
    ("addons", "shopify_connector_core", "static", "src", "v2"),
    # These test-only assets belong to the inert P16/V2 design trees.  The
    # currently declared unit-test assets (outside these prefixes) remain in
    # the archive so every manifest reference has an installable target.
    ("addons", "shopify_connector_core", "static", "tests", "p16"),
    ("addons", "shopify_connector_core", "static", "tests", "v2"),
    (
        "addons",
        "shopify_connector_core",
        "views",
        "shopify_connector_p16_admin_views.xml",
    ),
)
SECRET_VALUE_RE = re.compile(r"shpat_[A-Za-z0-9]{20,}", re.IGNORECASE)
PRIVATE_KEY_MARKER = "-----begin private key-----"
# These exact values are client-side redaction canaries in the retained HOOT
# unit-test asset.  They are deliberately not accepted as general secret
# material; any additional token-shaped value in a test asset still fails the
# source scan.
SYNTHETIC_TEST_SECRET_VALUES = frozenset(
    {
        "shpat_HOOT_MODE_SWITCH_LEAKCANARY".lower(),
        "shpat_HOOTDUMMY0000000000000000000000".lower(),
    }
)
FORBIDDEN_PRODUCT_CLAIMS = (
    "shopify app store",
    "oauth",
)


class PackageValidationError(ValueError):
    """Raised when the source tree cannot produce a safe distribution."""


def _edition(edition: str) -> str:
    """Return a supported edition name or raise a packaging error."""

    if edition not in EDITION_MODULES:
        choices = ", ".join(MARKETPLACE_EDITIONS)
        raise PackageValidationError(
            f"unknown marketplace edition {edition!r}; choose one of {choices}"
        )
    return edition


def _read_manifest(module_path: Path) -> dict:
    manifest_path = module_path / "__manifest__.py"
    _reject_symlink_components(manifest_path, "manifest source")
    try:
        source = manifest_path.read_text(encoding="utf-8")
    except (OSError, SyntaxError, ValueError, IndexError, AttributeError) as exc:
        raise PackageValidationError(
            f"{manifest_path}: manifest must be a literal Python dictionary"
        ) from exc
    return _parse_manifest(source, manifest_path)


def _parse_manifest(source: str, label: Path | str) -> dict:
    try:
        tree = ast.parse(source, str(label))
        value = ast.literal_eval(tree.body[0].value)
    except (SyntaxError, ValueError, IndexError, AttributeError) as exc:
        raise PackageValidationError(
            f"{label}: manifest must be a literal Python dictionary"
        ) from exc
    if not isinstance(value, dict):
        raise PackageValidationError(f"{label}: manifest is not a dictionary")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_excluded(path: Path) -> bool:
    try:
        relative_path = path.relative_to(REPO_ROOT)
    except ValueError:
        relative_path = path
    if any(
        relative_path.parts[: len(prefix)] == prefix
        for prefix in INERT_SOURCE_PATH_PREFIXES
    ):
        return True
    # Python test modules are intentionally left out of a marketplace
    # archive, but Odoo's manifest-declared static unit-test assets are part
    # of the source closure and must remain available in test mode.  Keep the
    # distinction explicit instead of excluding every directory named
    # ``tests``.
    if any(part in EXCLUDED_DIRECTORY_NAMES - {"tests"} for part in relative_path.parts):
        return True
    if "tests" in relative_path.parts:
        test_index = relative_path.parts.index("tests")
        if test_index == 0 or relative_path.parts[test_index - 1] != "static":
            return True
    name = path.name.lower()
    if name in EXCLUDED_FILE_NAMES or name.startswith(".env."):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    # Descriptive repository files do not belong in an Odoo addon bundle;
    # the manifest HTML is the only distribution description.
    if path.suffix.lower() in {".md", ".rst"}:
        return True
    return False


def _reject_symlink_components(path: Path, description: str) -> None:
    """Fail closed when any component of a package input is a symlink."""

    try:
        relative_path = path.relative_to(REPO_ROOT)
    except ValueError:
        if path.is_symlink():
            raise PackageValidationError(
                f"symlink is not allowed in {description}: {path}"
            )
        return
    current = REPO_ROOT
    for part in relative_path.parts:
        current /= part
        if current.is_symlink():
            raise PackageValidationError(
                f"symlink is not allowed in {description}: {current}"
            )


def _iter_module_files(module_name: str):
    module_path = ADDONS_ROOT / module_name
    _reject_symlink_components(module_path, "addon root")
    if not module_path.is_dir():
        raise PackageValidationError(f"missing companion addon: {module_name}")
    for path in sorted(module_path.rglob("*")):
        # A symlink inside an addon can point outside the repository and would
        # otherwise make ``read_bytes`` copy an unreviewed file into the
        # archive.  Marketplace artifacts must contain regular files owned by
        # this checkout only.
        _reject_symlink_components(path, "distribution source")
        if path.is_symlink():
            raise PackageValidationError(f"symlink is not allowed in distribution source: {path}")
        if path.is_file() and not _is_excluded(path):
            yield path.relative_to(REPO_ROOT)


def _validate_png(path: Path) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    try:
        with path.open("rb") as stream:
            header = stream.read(24)
    except OSError as exc:
        raise PackageValidationError(f"{path}: cannot read PNG") from exc
    if len(header) < 24 or header[:8] != signature or header[12:16] != b"IHDR":
        raise PackageValidationError(f"{path}: file is not a valid PNG header")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise PackageValidationError(f"{path}: PNG dimensions are empty")


def _validate_browser_evidence_source(relative_source: str) -> Path:
    """Return a marketplace image source only when its provenance is durable.

    The evidence directories carry a README describing how the screenshots
    were captured.  Requiring both that location and the provenance markers
    makes it difficult for a future packaging change to accidentally publish
    a static prototype capture as if it were an Odoo application screen.
    """

    relative_path = Path(relative_source)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise PackageValidationError(
            f"screenshot source must be a repository-relative browser-evidence path: "
            f"{relative_source}"
        )
    try:
        relative_path.relative_to(BROWSER_EVIDENCE_ROOT)
    except ValueError as exc:
        raise PackageValidationError(
            f"screenshot source must come from {BROWSER_EVIDENCE_ROOT}/: {relative_source}"
        ) from exc
    if "prototype" in relative_source.lower():
        raise PackageValidationError(
            f"prototype-only screenshot cannot be published as marketplace evidence: "
            f"{relative_source}"
        )

    source = REPO_ROOT / relative_path
    evidence_root = REPO_ROOT / BROWSER_EVIDENCE_ROOT
    _reject_symlink_components(source, "browser-evidence screenshot source")
    readme_path = None
    current = source.parent
    while current != evidence_root.parent:
        candidate = current / "README.md"
        if candidate.is_file():
            _reject_symlink_components(candidate, "browser-evidence provenance")
            readme_path = candidate
            break
        if current == evidence_root:
            break
        current = current.parent
    if readme_path is None:
        raise PackageValidationError(
            f"browser-evidence source has no durable provenance README: {relative_source}"
        )
    try:
        provenance = readme_path.read_text(encoding="utf-8").lower()
    except OSError as exc:
        raise PackageValidationError(
            f"cannot read browser-evidence provenance: {readme_path}"
        ) from exc
    missing = [marker for marker in BROWSER_EVIDENCE_README_MARKERS if marker not in provenance]
    if missing:
        raise PackageValidationError(
            f"browser-evidence provenance is incomplete for {relative_source}: "
            f"missing {', '.join(missing)}"
        )
    return source


def _validate_meta_module(edition: str = "full") -> dict:
    edition = _edition(edition)
    meta_module = EDITION_META_MODULES[edition]
    meta_dependencies = EDITION_META_DEPENDENCIES[edition]
    image_sources = EDITION_IMAGE_SOURCES[edition]
    module_path = ADDONS_ROOT / meta_module
    _reject_symlink_components(module_path, "addon root")
    if not module_path.is_dir():
        raise PackageValidationError(f"missing meta module: {module_path}")
    manifest = _read_manifest(module_path)
    if manifest.get("name") != EDITION_MANIFEST_NAMES[edition]:
        raise PackageValidationError(
            f"{edition} meta module name is not {EDITION_MANIFEST_NAMES[edition]}"
        )
    if not str(manifest.get("version", "")).startswith("19.0."):
        raise PackageValidationError(f"{edition} meta module version must target Odoo 19")
    if manifest.get("license") != "LGPL-3":
        raise PackageValidationError(f"{edition} meta module license must be LGPL-3")
    if manifest.get("author") != "Adams":
        raise PackageValidationError(
            f"{edition} meta module author must reuse the repository's existing Adams value"
        )
    if manifest.get("application") is not True or manifest.get("installable") is not True:
        raise PackageValidationError(f"{edition} meta module must be an installable application")
    if manifest.get("auto_install") is not False:
        raise PackageValidationError(f"{edition} meta module must not auto-install")
    if list(manifest.get("depends", ())) != list(meta_dependencies):
        raise PackageValidationError(
            f"{edition} meta module dependencies must exactly cover its edition closure"
        )
    for key in ("data", "demo", "assets"):
        if manifest.get(key):
            raise PackageValidationError(f"meta module must not define {key}")
    init_path = module_path / "__init__.py"
    _reject_symlink_components(init_path, "meta-addon initializer")
    if init_path.read_text(encoding="utf-8").count("import"):
        raise PackageValidationError("meta module __init__.py must not import behavior")

    allowed_top_level = {"__init__.py", "__manifest__.py", "images", "static", "README.md"}
    for entry in module_path.iterdir():
        _reject_symlink_components(entry, "meta-addon source")
        # Importing the validator itself may create bytecode beside the meta
        # module before validation runs.  Generated caches are already
        # excluded from every archive entry; ignore only those exact generated
        # artifacts here while continuing to reject unknown source content.
        if entry.name in EXCLUDED_DIRECTORY_NAMES or entry.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        if entry.name not in allowed_top_level:
            raise PackageValidationError(
                f"{edition} meta module contains unexpected entry: {entry}"
            )
    description_path = module_path / "static" / "description" / "index.html"
    icon_path = module_path / "static" / "description" / "icon.png"
    _reject_symlink_components(description_path, "meta-addon description")
    _reject_symlink_components(icon_path, "meta-addon icon")
    if not description_path.is_file() or not icon_path.is_file():
        raise PackageValidationError(
            f"{edition} meta module needs static/description/index.html and icon.png"
        )
    _validate_png(icon_path)

    description = (
        description_path.read_text(encoding="utf-8")
        + "\n"
        + repr(manifest.get("description", ""))
    ).lower()
    for forbidden in FORBIDDEN_PRODUCT_CLAIMS:
        if forbidden in description:
            raise PackageValidationError(
                f"meta module presentation contains forbidden claim/reference: {forbidden}"
            )
    images = manifest.get("images")
    if not isinstance(images, list) or list(images) != list(image_sources):
        raise PackageValidationError("manifest images must match the bounded evidence selection")
    for relative_target, relative_source in image_sources.items():
        target = module_path / relative_target
        source = _validate_browser_evidence_source(relative_source)
        _reject_symlink_components(target, "marketplace screenshot target")
        if not target.is_file() or not source.is_file():
            raise PackageValidationError(f"missing screenshot source or copy: {relative_source}")
        _validate_png(target)
        if _sha256(target) != _sha256(source):
            raise PackageValidationError(
                f"screenshot copy differs from accepted evidence source: {relative_target}"
            )
    return manifest


def _validate_companions(edition: str = "full") -> None:
    edition = _edition(edition)
    available = set(EDITION_MODULES[edition])
    for module_name in EDITION_MODULES[edition][1:]:
        module_path = ADDONS_ROOT / module_name
        _reject_symlink_components(module_path, "addon root")
        if not module_path.is_dir():
            raise PackageValidationError(f"missing companion addon: {module_name}")
        manifest = _read_manifest(module_path)
        for dependency in manifest.get("depends", ()):
            if dependency not in available and dependency not in ODOO_BUILTIN_DEPENDENCIES:
                raise PackageValidationError(
                    f"{module_name}: dependency {dependency!r} is not bundled or an Odoo base addon"
                )


def _validate_source_markers(edition: str = "full") -> None:
    edition = _edition(edition)
    for module_name in EDITION_MODULES[edition]:
        for relative_path in _iter_module_files(module_name):
            path = REPO_ROOT / relative_path
            if path.suffix.lower() not in {".py", ".xml", ".csv", ".js", ".scss", ".html", ".txt"}:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError as exc:
                raise PackageValidationError(f"cannot read {relative_path}") from exc
            secret_values = set(SECRET_VALUE_RE.findall(content))
            synthetic_test_canaries_only = (
                "static" in relative_path.parts
                and "tests" in relative_path.parts
                and secret_values <= SYNTHETIC_TEST_SECRET_VALUES
            )
            if PRIVATE_KEY_MARKER in content or (
                secret_values and not synthetic_test_canaries_only
            ):
                raise PackageValidationError(
                    f"credential material found in distribution file {relative_path}"
                )


def _validate_license() -> None:
    path = REPO_ROOT / LICENSE_PATH
    _reject_symlink_components(path, "distribution license")
    if not path.is_file():
        raise PackageValidationError(
            f"distribution license is missing: {LICENSE_PATH}"
        )
    if _sha256(path) != LICENSE_SHA256:
        raise PackageValidationError(
            "LICENSE must be the checked-in verbatim LGPL-3 text "
            f"(expected SHA256 {LICENSE_SHA256})"
        )
    text = path.read_text(encoding="utf-8")
    for marker in (
        "GNU LESSER GENERAL PUBLIC LICENSE",
        "Version 3, 29 June 2007",
        "If the Library as you received it specifies",
    ):
        if marker not in text:
            raise PackageValidationError(f"LICENSE is missing required marker: {marker}")


def validate_source_tree(edition: str = "full") -> tuple[Path, ...]:
    """Validate and return repository-relative package files for one edition."""

    edition = _edition(edition)
    _validate_license()
    _validate_meta_module(edition)
    _validate_companions(edition)
    _validate_source_markers(edition)
    files = ROOT_DISTRIBUTION_FILES + tuple(
        relative_path
        for module_name in EDITION_MODULES[edition]
        for relative_path in _iter_module_files(module_name)
    )
    if not files:
        raise PackageValidationError("no package files found")
    return files


def _zip_name(relative_path: Path) -> str:
    path = relative_path.as_posix()
    if path.startswith("addons/"):
        return path[len("addons/") :]
    return path


def _manifest_archive_references(module_name: str, manifest: dict) -> tuple[str, ...]:
    """Return every archive path named by a module manifest.

    ``data``, ``demo``, and ``images`` are module-relative in Odoo manifests;
    asset bundles use the addon-qualified path that Odoo resolves from the
    addons path.  Keeping this normalization in one place lets both the
    builder and the extracted-archive test enforce the same closure.
    """

    references: list[str] = []
    for key in ("data", "demo", "images"):
        values = manifest.get(key) or ()
        if not isinstance(values, (list, tuple)):
            raise PackageValidationError(
                f"{module_name}: manifest {key!r} must be a list or tuple"
            )
        for value in values:
            if not isinstance(value, str) or not value:
                raise PackageValidationError(
                    f"{module_name}: manifest {key!r} contains a non-path value"
                )
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise PackageValidationError(
                    f"{module_name}: manifest {key!r} contains unsafe path {value!r}"
                )
            references.append(f"{module_name}/{path.as_posix()}")

    assets = manifest.get("assets") or {}
    if not isinstance(assets, dict):
        raise PackageValidationError(f"{module_name}: manifest assets must be a dictionary")
    for bundle, values in assets.items():
        if not isinstance(bundle, str) or not isinstance(values, (list, tuple)):
            raise PackageValidationError(
                f"{module_name}: manifest asset bundle {bundle!r} is malformed"
            )
        for value in values:
            # Odoo supports a small tuple syntax for directives such as
            # ``('include', 'web.assets_common')``.  Such a directive names a
            # bundle rather than a source file and therefore has no archive
            # path to close.  All string entries, including web.assets_tests
            # browser tours and web.assets_unit_tests files, must be present.
            if isinstance(value, (list, tuple)):
                if value and value[0] in {
                    "append",
                    "before",
                    "after",
                    "include",
                    "prepend",
                    "remove",
                }:
                    continue
                raise PackageValidationError(
                    f"{module_name}: manifest asset bundle {bundle!r} contains "
                    "an unsupported directive"
                )
            if not isinstance(value, str) or not value:
                raise PackageValidationError(
                    f"{module_name}: manifest asset bundle {bundle!r} contains a non-path value"
                )
            path = value.replace("\\", "/")
            if path.startswith("/") or "../" in f"{path}/":
                raise PackageValidationError(
                    f"{module_name}: manifest asset bundle {bundle!r} contains "
                    f"unsafe path {value!r}"
                )
            references.append(path)
    return tuple(references)


def _archive_reference_exists(reference: str, archive_names: set[str]) -> bool:
    """Return whether an exact or glob asset reference resolves in an archive."""

    return any(fnmatch.fnmatchcase(name, reference) for name in archive_names)


def validate_archive_manifest_closure(
    archive_path: Path, edition: str = "full"
) -> tuple[str, ...]:
    """Validate manifests and their install/file closure from a ZIP archive.

    Source-checkout validation is not sufficient: the exclusion policy can
    remove a path after its source manifest was inspected.  This pass reads
    the generated archive itself, verifies that bundled dependencies have
    manifests, and resolves every declared data/demo/image/asset reference.
    """

    edition = _edition(edition)
    archive_path = Path(archive_path)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = tuple(info.filename for info in infos)
            name_set = set(names)
            if len(names) != len(name_set):
                raise PackageValidationError("archive contains duplicate file names")
            for info in infos:
                path = Path(info.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise PackageValidationError(
                        f"archive contains unsafe path: {info.filename}"
                    )
                # ZIP symlink entries can masquerade as regular files unless
                # their Unix mode is inspected explicitly.
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and (mode & 0o170000) == 0o120000:
                    raise PackageValidationError(
                        f"archive contains a symlink entry: {info.filename}"
                    )

            available = set(EDITION_MODULES[edition])
            for module_name in EDITION_MODULES[edition]:
                manifest_name = f"{module_name}/__manifest__.py"
                if manifest_name not in name_set:
                    raise PackageValidationError(
                        f"archive is missing bundled manifest: {manifest_name}"
                    )
                try:
                    manifest_source = archive.read(manifest_name).decode("utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    raise PackageValidationError(
                        f"cannot read bundled manifest: {manifest_name}"
                    ) from exc
                manifest = _parse_manifest(manifest_source, manifest_name)
                for dependency in manifest.get("depends", ()):
                    if dependency not in available and dependency not in ODOO_BUILTIN_DEPENDENCIES:
                        raise PackageValidationError(
                            f"{module_name}: archive dependency {dependency!r} is not "
                            "bundled or an Odoo base addon"
                        )
                for reference in _manifest_archive_references(module_name, manifest):
                    if not _archive_reference_exists(reference, name_set):
                        raise PackageValidationError(
                            f"{module_name}: archive manifest reference is missing: {reference}"
                        )
            if "LICENSE" not in name_set:
                raise PackageValidationError("archive is missing root LICENSE")
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackageValidationError(f"invalid distribution archive: {archive_path}") from exc
    return names


def _validate_output_path(output: Path) -> Path:
    """Validate a destination before any source tree or output write occurs."""

    output = Path(output)
    if output.suffix.lower() != ".zip":
        raise PackageValidationError(
            f"distribution output must use the .zip suffix: {output}"
        )
    if output.is_symlink():
        raise PackageValidationError(f"distribution output cannot be a symlink: {output}")
    # Check both the lexical path and its resolved destination.  The first
    # closes the obvious ``repo/../`` and in-repository cases; the second
    # closes an outside path whose parent symlink points back into the source
    # checkout.  Build output belongs beside the repository, never in it.
    lexical = Path(os.path.abspath(os.fspath(output)))
    try:
        resolved = output.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise PackageValidationError(
            f"cannot resolve distribution output path: {output}"
        ) from exc
    for candidate in (lexical, resolved):
        if candidate == REPO_ROOT or REPO_ROOT in candidate.parents:
            raise PackageValidationError(
                f"distribution output must be outside the repository source tree: {output}"
            )
    return resolved


def build_bundle(output: Path, edition: str = "full") -> tuple[str, ...]:
    """Validate one edition and write a reproducible ZIP archive."""

    output = _validate_output_path(output)
    files = validate_source_tree(edition)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = tuple(_zip_name(path) for path in files)
    if len(entries) != len(set(entries)):
        raise PackageValidationError("distribution source maps to duplicate archive paths")
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative_path, archive_name in zip(files, entries):
            source = REPO_ROOT / relative_path
            info = zipfile.ZipInfo(archive_name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    validate_archive_manifest_closure(output, edition)
    return entries


def _default_output(edition: str = "full") -> Path:
    edition = _edition(edition)
    meta_module = EDITION_META_MODULES[edition]
    version = _read_manifest(ADDONS_ROOT / meta_module).get("version", "19.0.0.0.0")
    # Keep generated artifacts outside the checkout so they cannot be picked
    # up as source inputs or leave a dirty release tree.
    return REPO_ROOT.parent / f"{REPO_ROOT.name}-dist" / f"{meta_module}-{version}.zip"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--edition",
        choices=MARKETPLACE_EDITIONS,
        default="full",
        help="marketplace edition to validate/build (default: full)",
    )
    parser.add_argument(
        "--all-editions",
        action="store_true",
        help="validate/build both DEC-029 marketplace editions",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the source tree without writing an archive",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and list archive entries without writing an archive",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="archive path outside the repository (default: sibling <repo>-dist directory)",
    )
    args = parser.parse_args(argv)
    if args.all_editions and args.output is not None:
        parser.error("--output cannot be combined with --all-editions")
    editions = MARKETPLACE_EDITIONS if args.all_editions else (args.edition,)
    try:
        if args.check:
            for edition in editions:
                files = validate_source_tree(edition)
                print(f"OK: {edition}: {len(files)} distribution files validated")
            return 0
        if args.dry_run:
            for edition in editions:
                files = validate_source_tree(edition)
                print(f"[{edition}]")
                for relative_path in files:
                    print(_zip_name(relative_path))
                print(f"OK: {edition}: {len(files)} distribution files; archive not written")
            return 0
        for edition in editions:
            output = args.output or _default_output(edition)
            entries = build_bundle(output, edition)
            print(f"OK: wrote {output} ({len(entries)} files)")
        return 0
    except PackageValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
