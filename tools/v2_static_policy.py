#!/usr/bin/env python3
"""Fast, dependency-free static policy checks for local Odoo addons.

The validator is deliberately fail-closed and read-only.  It does not import
Odoo, evaluate a manifest as Python, contact a service, or write a generated
artifact.  Run it from any directory with ``--repo-root`` pointing at the
repository to inspect.
"""

import argparse
import ast
import builtins
import csv
import re
import symtable
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree


ACL_REQUIRED_COLUMNS = frozenset({
    "id",
    "name",
    "model_id:id",
    "group_id:id",
    "perm_read",
    "perm_write",
    "perm_create",
    "perm_unlink",
})
ASSET_DIRECTIVES = {
    "append": 1,
    "prepend": 1,
    "before": 2,
    "after": 2,
    "replace": 2,
    "remove": 1,
    "include": 0,
}
LOCAL_ASSET_DIRECTORIES = frozenset({
    "data",
    "demo",
    "i18n",
    "models",
    "report",
    "security",
    "static",
    "tests",
    "views",
    "wizard",
    "wizards",
})
EXTERNAL_ID_TAGS = frozenset({
    "act_window",
    "delete",
    "function",
    "menuitem",
    "record",
    "report",
    "server_action",
    "template",
    "workflow",
})
EXTERNAL_ID_RE = re.compile(
    r"<\s*(?:[A-Za-z_][\w.-]*:)?(?P<tag>act_window|delete|function|"
    r"menuitem|record|report|server_action|template|workflow)\b"
    r"(?P<attributes>[^>]*?)\bid\s*=\s*(?P<quote>['\"])(?P<id>[^'\"]+)"
    r"(?P=quote)",
    re.DOTALL,
)


@dataclass(frozen=True)
class PolicyViolation:
    """One concise, source-located policy failure."""

    path: str
    line: int
    rule: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


# Short aliases make the result convenient for callers without prescribing a
# particular test-runner integration.
Violation = PolicyViolation


@dataclass(frozen=True)
class _Manifest:
    path: Path
    addon_root: Path
    identity: str
    value: dict[Any, Any]
    key_nodes: dict[str, ast.AST]


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _line(value: Any, default: int = 1) -> int:
    candidate = getattr(value, "lineno", value)
    return candidate if isinstance(candidate, int) and candidate > 0 else default


def _violation(
    root: Path,
    path: Path,
    line: int,
    rule: str,
    message: str,
) -> PolicyViolation:
    return PolicyViolation(_relative(root, path), _line(line), rule, message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _manifest_paths(addons_root: Path) -> list[Path]:
    return sorted(
        path for path in addons_root.rglob("__manifest__.py") if path.is_file()
    )


def _parse_manifest(
    root: Path,
    path: Path,
) -> tuple[_Manifest | None, list[PolicyViolation]]:
    violations: list[PolicyViolation] = []
    try:
        source = _read(path)
    except (OSError, UnicodeError) as exc:
        return None, [_violation(
            root, path, 1, "manifest-literal", f"cannot read manifest: {exc}")]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return None, [_violation(
            root,
            path,
            exc.lineno or 1,
            "manifest-literal",
            f"manifest is not valid Python: {exc.msg}",
        )]

    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        return None, [_violation(
            root,
            path,
            _line(tree.body[0]) if tree.body else 1,
            "manifest-literal",
            "manifest must be a single literal dictionary",
        )]

    expression = tree.body[0].value
    try:
        value = ast.literal_eval(expression)
    except (SyntaxError, TypeError, ValueError) as exc:
        return None, [_violation(
            root,
            path,
            _line(expression),
            "manifest-literal",
            f"manifest must contain literal values: {exc}",
        )]
    if not isinstance(value, dict):
        return None, [_violation(
            root,
            path,
            _line(expression),
            "manifest-literal",
            "manifest must evaluate to a dictionary",
        )]

    key_nodes: dict[str, ast.AST] = {}
    if isinstance(expression, ast.Dict):
        for key_node, value_node in zip(expression.keys, expression.values):
            if key_node is None:
                continue
            try:
                key = ast.literal_eval(key_node)
            except (SyntaxError, TypeError, ValueError):
                continue
            if isinstance(key, str):
                key_nodes[key] = value_node

    return _Manifest(
        path=path,
        addon_root=path.parent,
        identity=path.parent.name,
        value=value,
        key_nodes=key_nodes,
    ), violations


def _addon_roots(manifest_paths: list[Path]) -> list[Path]:
    return sorted({path.parent for path in manifest_paths})


def _all_files(addon_roots: list[Path], suffix: str) -> list[Path]:
    paths: set[Path] = set()
    for addon_root in addon_roots:
        paths.update(path for path in addon_root.rglob(f"*{suffix}") if path.is_file())
    return sorted(paths)


def _parse_python_files(
    root: Path,
    paths: list[Path],
    exclude: set[Path] | None = None,
) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    excluded = exclude or set()
    for path in paths:
        if path in excluded:
            continue
        try:
            source = _read(path)
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            violations.append(_violation(
                root,
                path,
                exc.lineno or 1,
                "python-syntax",
                f"cannot parse Python: {exc.msg}",
            ))
        except (OSError, UnicodeError) as exc:
            violations.append(_violation(
                root, path, 1, "python-syntax", f"cannot read Python: {exc}")
            )
    return violations


_IMPLICIT_MODULE_GLOBALS = frozenset({
    "__builtins__",
    "__cached__",
    "__file__",
    "__loader__",
    "__name__",
    "__package__",
    "__spec__",
})


def _check_python_globals(
    root: Path,
    paths: list[Path],
    exclude: set[Path] | None = None,
) -> list[PolicyViolation]:
    """Reject unresolved module globals before an Odoo registry load.

    Python compilation accepts a misspelled or forgotten import and defers the
    failure until the affected method executes.  ``symtable`` distinguishes a
    genuine module-global lookup from locals, closures and class attributes,
    which keeps this check dependency-free and useful for split modules.
    """

    violations: list[PolicyViolation] = []
    excluded = exclude or set()
    allowed = frozenset(dir(builtins)) | _IMPLICIT_MODULE_GLOBALS
    for path in paths:
        if path in excluded:
            continue
        try:
            source = _read(path)
            tree = ast.parse(source, filename=str(path))
            table = symtable.symtable(source, str(path), "exec")
        except SyntaxError:
            # The syntax pass owns the precise diagnostic.
            continue
        except (OSError, UnicodeError):
            continue

        module_definitions = {
            symbol.get_name()
            for symbol in table.get_symbols()
            if symbol.is_assigned()
            or symbol.is_imported()
            or symbol.is_namespace()
        }
        first_load_line: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                first_load_line.setdefault(node.id, node.lineno)

        unresolved: set[str] = set()
        pending = list(table.get_children())
        while pending:
            child = pending.pop()
            pending.extend(child.get_children())
            for symbol in child.get_symbols():
                name = symbol.get_name()
                if (
                    symbol.is_referenced()
                    and symbol.is_global()
                    and name not in module_definitions
                    and name not in allowed
                ):
                    unresolved.add(name)
        for name in sorted(unresolved):
            violations.append(_violation(
                root,
                path,
                first_load_line.get(name, 1),
                "python-unresolved-global",
                f"{name!r} is referenced as a module global but is not "
                "defined or imported",
            ))
    return violations


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _has_magic(value: str) -> bool:
    return any(character in value for character in "*?[")


def _safe_reference(value: str) -> tuple[PurePosixPath | None, str | None]:
    if not value or "\\" in value:
        return None, "reference must be a non-empty relative POSIX path"
    reference = PurePosixPath(value)
    if reference.is_absolute():
        return None, "reference must be relative to an addon"
    if ".." in reference.parts:
        return None, "reference may not escape its addon"
    if not reference.parts or reference == PurePosixPath("."):
        return None, "reference must name a file"
    return reference, None


def _reference_owner(
    record: _Manifest,
    reference: PurePosixPath,
    kind: str,
    addon_by_identity: dict[str, Path],
) -> tuple[Path | None, PurePosixPath]:
    first = reference.parts[0]
    if first in addon_by_identity:
        return addon_by_identity[first], PurePosixPath(*reference.parts[1:])

    # Asset paths may point at a declared external Odoo dependency (for
    # example ``web/static/...``).  Those files are not part of this local
    # repository and must not be mistaken for missing local assets.  Data/demo
    # files, however, are always addon-local in an Odoo manifest.
    if kind == "asset":
        dependencies = record.value.get("depends", ())
        if isinstance(dependencies, (list, tuple, set)) and first in dependencies:
            return None, reference
    return record.addon_root, reference


def _check_file_reference(
    root: Path,
    record: _Manifest,
    kind: str,
    raw_reference: Any,
    source_node: ast.AST | None,
    addon_by_identity: dict[str, Path],
    violations: list[PolicyViolation],
) -> None:
    line = _line(source_node)
    if not isinstance(raw_reference, str):
        violations.append(_violation(
            root,
            record.path,
            line,
            "manifest-reference",
            f"{kind} reference must be a string",
        ))
        return
    reference, error = _safe_reference(raw_reference)
    if error:
        violations.append(_violation(
            root, record.path, line, "manifest-reference", f"{kind}: {error}")
        )
        return

    owner, relative = _reference_owner(
        record, reference, kind, addon_by_identity)
    if owner is None:
        return
    if not relative.parts:
        violations.append(_violation(
            root,
            record.path,
            line,
            "manifest-reference",
            f"{kind} reference {raw_reference!r} must name a file",
        ))
        return

    pattern = relative.as_posix()
    owner_resolved = owner.resolve()
    if not _is_inside(owner_resolved, root / "addons"):
        violations.append(_violation(
            root,
            record.path,
            line,
            "manifest-reference",
            f"{kind} reference owner escapes the addons directory",
        ))
        return

    if _has_magic(pattern):
        try:
            matches = list(owner.glob(pattern))
        except (OSError, ValueError) as exc:
            violations.append(_violation(
                root,
                record.path,
                line,
                "manifest-reference",
                f"invalid {kind} glob {raw_reference!r}: {exc}",
            ))
            return
        local_files = [
            match for match in matches
            if match.is_file() and _is_inside(match, root / "addons")
        ]
        if not local_files:
            violations.append(_violation(
                root,
                record.path,
                line,
                "manifest-reference",
                f"{kind} glob {raw_reference!r} matched no local files",
            ))
        return

    target = owner.joinpath(*relative.parts)
    if not target.is_file():
        violations.append(_violation(
            root,
            record.path,
            line,
            "manifest-reference",
            f"{kind} reference {raw_reference!r} does not exist",
        ))
    elif not _is_inside(target, root / "addons"):
        violations.append(_violation(
            root,
            record.path,
            line,
            "manifest-reference",
            f"{kind} reference {raw_reference!r} escapes the addons directory",
        ))


def _check_manifest_references(
    root: Path,
    record: _Manifest,
    addon_by_identity: dict[str, Path],
    violations: list[PolicyViolation],
) -> None:
    for key in ("data", "demo"):
        value = record.value.get(key)
        if value is None:
            continue
        node = record.key_nodes.get(key)
        if not isinstance(value, (list, tuple)):
            violations.append(_violation(
                root,
                record.path,
                _line(node),
                "manifest-reference",
                f"manifest {key!r} must be a list or tuple",
            ))
            continue
        node_values = list(node.elts) if isinstance(node, (ast.List, ast.Tuple)) else []
        for index, item in enumerate(value):
            item_node = node_values[index] if index < len(node_values) else node
            _check_file_reference(
                root,
                record,
                key,
                item,
                item_node,
                addon_by_identity,
                violations,
            )

    assets = record.value.get("assets")
    if assets is None:
        return
    assets_node = record.key_nodes.get("assets")
    if not isinstance(assets, dict):
        violations.append(_violation(
            root,
            record.path,
            _line(assets_node),
            "manifest-reference",
            "manifest 'assets' must be a dictionary",
        ))
        return

    node_items = (
        list(zip(assets_node.keys, assets_node.values))
        if isinstance(assets_node, ast.Dict)
        else []
    )
    node_by_bundle: dict[str, ast.AST] = {}
    for key_node, value_node in node_items:
        try:
            bundle = ast.literal_eval(key_node) if key_node is not None else None
        except (SyntaxError, TypeError, ValueError):
            bundle = None
        if isinstance(bundle, str):
            node_by_bundle[bundle] = value_node

    for bundle, entries in assets.items():
        bundle_node = node_by_bundle.get(bundle, assets_node)
        if not isinstance(bundle, str):
            violations.append(_violation(
                root,
                record.path,
                _line(bundle_node),
                "manifest-reference",
                "asset bundle names must be strings",
            ))
            continue
        if not isinstance(entries, (list, tuple)):
            violations.append(_violation(
                root,
                record.path,
                _line(bundle_node),
                "manifest-reference",
                f"asset bundle {bundle!r} must be a list or tuple",
            ))
            continue

        entry_nodes = (
            list(bundle_node.elts)
            if isinstance(bundle_node, (ast.List, ast.Tuple))
            else []
        )
        for index, entry in enumerate(entries):
            entry_node = entry_nodes[index] if index < len(entry_nodes) else bundle_node
            if isinstance(entry, str):
                references = [(entry, entry_node)]
            elif isinstance(entry, (list, tuple)):
                operation = entry[0] if entry else None
                expected = ASSET_DIRECTIVES.get(operation)
                if expected is None or len(entry) - 1 != expected:
                    violations.append(_violation(
                        root,
                        record.path,
                        _line(entry_node),
                        "manifest-reference",
                        "asset directive must be a supported operation with "
                        "the expected number of paths",
                    ))
                    continue
                # include names a bundle, not a local file.  Every other
                # directive path is a local/external asset reference.
                references = [] if operation == "include" else [
                    (path, entry_node) for path in entry[1:]
                ]
            else:
                violations.append(_violation(
                    root,
                    record.path,
                    _line(entry_node),
                    "manifest-reference",
                    "asset entries must be strings or supported directives",
                ))
                continue

            for reference, reference_node in references:
                _check_file_reference(
                    root,
                    record,
                    "asset",
                    reference,
                    reference_node,
                    addon_by_identity,
                    violations,
                )


def _check_xml_files(root: Path, paths: list[Path]) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    for path in paths:
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as exc:
            position = getattr(exc, "position", (1, 0))
            line = position[0] if position else 1
            violations.append(_violation(
                root,
                path,
                line,
                "xml-syntax",
                f"cannot parse XML: {exc.msg}",
            ))
        except (OSError, UnicodeError) as exc:
            violations.append(_violation(
                root, path, 1, "xml-syntax", f"cannot read XML: {exc}")
            )
    return violations


def _owner_for_path(path: Path, addon_roots: list[Path]) -> Path | None:
    owners = [addon for addon in addon_roots if _is_inside(path, addon)]
    return max(owners, key=lambda addon: len(addon.parts)) if owners else None


def _xml_external_id_rows(path: Path) -> list[tuple[str, int]]:
    """Return record-like XML external IDs and best-effort source lines."""
    try:
        tree = ElementTree.parse(path)
        source = _read(path)
    except (ElementTree.ParseError, OSError, UnicodeError):
        # The XML syntax pass owns the diagnostic for malformed/unreadable
        # files.  There is no safe identity result to derive from them here.
        return []

    lines_by_id: dict[str, list[int]] = defaultdict(list)
    for match in EXTERNAL_ID_RE.finditer(source):
        external_id = match.group("id")
        lines_by_id[external_id].append(source.count("\n", 0, match.start()) + 1)

    rows: list[tuple[str, int]] = []
    for element in tree.getroot().iter():
        if not isinstance(element.tag, str):
            continue
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in EXTERNAL_ID_TAGS:
            continue
        external_id = element.get("id")
        if not external_id:
            continue
        candidates = lines_by_id.get(external_id, [])
        line = candidates.pop(0) if candidates else 1
        rows.append((external_id, line))
    return rows


def _check_duplicate_xml_ids(
    root: Path,
    addon_roots: list[Path],
    paths: list[Path],
) -> list[PolicyViolation]:
    by_addon: dict[Path, list[Path]] = defaultdict(list)
    for path in paths:
        owner = _owner_for_path(path, addon_roots)
        if owner is not None:
            by_addon[owner].append(path)

    violations: list[PolicyViolation] = []
    for addon, addon_paths in sorted(by_addon.items()):
        seen: dict[str, tuple[Path, int]] = {}
        for path in sorted(addon_paths):
            for external_id, line in _xml_external_id_rows(path):
                previous = seen.get(external_id)
                if previous is not None:
                    previous_path, _previous_line = previous
                    violations.append(_violation(
                        root,
                        path,
                        line,
                        "xml-duplicate-id",
                        f"external ID {external_id!r} is also defined in "
                        f"{_relative(root, previous_path)}",
                    ))
                else:
                    seen[external_id] = (path, line)
    return violations


def _check_csv_file(root: Path, path: Path) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    header: list[str] | None = None
    header_line = 1
    reader = None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            for row in reader:
                line = reader.line_num
                # Empty physical lines are harmless separators; a non-empty
                # first row remains mandatory as the column header.
                if not row:
                    continue
                if header is None:
                    header = list(row)
                    header_line = line
                    if header:
                        header[0] = header[0].lstrip("\ufeff")
                    if path.name == "ir.model.access.csv":
                        missing = sorted(ACL_REQUIRED_COLUMNS - set(header))
                        if missing:
                            violations.append(_violation(
                                root,
                                path,
                                header_line,
                                "acl-header",
                                "missing required columns: " + ", ".join(missing),
                            ))
                    continue
                if len(row) != len(header):
                    violations.append(_violation(
                        root,
                        path,
                        line,
                        "csv-shape",
                        f"row has {len(row)} columns; header has {len(header)}",
                    ))
    except csv.Error as exc:
        violations.append(_violation(
            root,
            path,
            reader.line_num if reader is not None else 1,
            "csv-syntax",
            f"cannot parse CSV: {exc}",
        ))
    except (OSError, UnicodeError) as exc:
        violations.append(_violation(
            root, path, 1, "csv-syntax", f"cannot read CSV: {exc}")
        )

    if header is None:
        violations.append(_violation(
            root, path, 1, "csv-shape", "CSV must contain a header row")
        )
    return violations


def _acl_external_id_rows(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    header: list[str] | None = None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            for row in reader:
                if not row:
                    continue
                if header is None:
                    header = list(row)
                    if header:
                        header[0] = header[0].lstrip("\ufeff")
                    continue
                if len(row) != len(header):
                    continue
                if not ACL_REQUIRED_COLUMNS.issubset(header):
                    return []
                external_id = row[header.index("id")].strip()
                if external_id:
                    rows.append((external_id, reader.line_num))
    except (csv.Error, OSError, UnicodeError):
        return rows
    return rows if header and ACL_REQUIRED_COLUMNS.issubset(header) else []


def _check_duplicate_acl_ids(
    root: Path,
    addon_roots: list[Path],
    paths: list[Path],
) -> list[PolicyViolation]:
    by_addon: dict[Path, list[Path]] = defaultdict(list)
    for path in paths:
        owner = _owner_for_path(path, addon_roots)
        if owner is not None:
            by_addon[owner].append(path)

    violations: list[PolicyViolation] = []
    for _addon, addon_paths in sorted(by_addon.items()):
        seen: dict[str, tuple[Path, int]] = {}
        for path in sorted(addon_paths):
            for external_id, line in _acl_external_id_rows(path):
                previous = seen.get(external_id)
                if previous is not None:
                    previous_path, _previous_line = previous
                    violations.append(_violation(
                        root,
                        path,
                        line,
                        "acl-duplicate-id",
                        f"ACL external ID {external_id!r} is also defined in "
                        f"{_relative(root, previous_path)}",
                    ))
                else:
                    seen[external_id] = (path, line)
    return violations


def _imported_test_modules(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 1:
                if node.module:
                    candidate = node.module.rsplit(".", 1)[-1]
                    if candidate.startswith("test_"):
                        imported.add(candidate)
                else:
                    imported.update(
                        alias.name for alias in node.names
                        if alias.name.startswith("test_")
                    )
            elif node.level == 0 and node.module:
                parts = node.module.split(".")
                if "tests" in parts:
                    imported.update(
                        alias.name for alias in node.names
                        if alias.name.startswith("test_")
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) >= 2 and "tests" in parts:
                    candidate = parts[-1]
                    if candidate.startswith("test_"):
                        imported.add(candidate)
    return imported


def _check_test_discovery(
    root: Path,
    addon_roots: list[Path],
) -> list[PolicyViolation]:
    violations: list[PolicyViolation] = []
    tests_directories = sorted({
        path
        for addon_root in addon_roots
        for path in addon_root.rglob("tests")
        if path.is_dir()
    })
    test_package_directories = sorted({
        path.parent
        for tests_directory in tests_directories
        for path in tests_directory.rglob("test_*.py")
        if path.is_file()
    })
    for tests_directory in test_package_directories:
        test_files = sorted(tests_directory.glob("test_*.py"))
        if not test_files:
            # A test file below a package is checked against that package's
            # __init__, so this branch is only defensive for a disappearing
            # file in a concurrently changing tree.
            continue
        init_path = tests_directory / "__init__.py"
        if not init_path.is_file():
            violations.append(_violation(
                root,
                init_path,
                1,
                "test-discovery",
                "tests package is missing __init__.py",
            ))
            imported: set[str] = set()
        else:
            try:
                tree = ast.parse(_read(init_path), filename=str(init_path))
                imported = _imported_test_modules(tree)
            except SyntaxError:
                # The Python syntax pass owns the precise syntax diagnostic.
                imported = set()
            except (OSError, UnicodeError):
                imported = set()
        for test_file in test_files:
            if test_file.stem not in imported:
                violations.append(_violation(
                    root,
                    test_file,
                    1,
                    "test-discovery",
                    f"{test_file.name} is not imported by "
                    f"{_relative(root, init_path)}",
                ))
    return violations


def _check_duplicate_identities(
    root: Path,
    manifests: list[_Manifest],
) -> list[PolicyViolation]:
    by_identity: dict[str, list[_Manifest]] = defaultdict(list)
    for manifest in manifests:
        by_identity[manifest.identity].append(manifest)
    violations: list[PolicyViolation] = []
    for identity, records in sorted(by_identity.items()):
        if len(records) < 2:
            continue
        first = records[0]
        for duplicate in records[1:]:
            violations.append(_violation(
                root,
                duplicate.path,
                1,
                "duplicate-addon-identity",
                f"technical addon identity {identity!r} is also declared by "
                f"{_relative(root, first.path)}",
            ))
    return violations


def check_repository(repo_root: str | Path) -> list[PolicyViolation]:
    """Return deterministic static-policy violations for ``repo_root``."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")
    addons_root = root / "addons"
    if not addons_root.is_dir():
        raise ValueError(f"repository has no addons directory: {addons_root}")

    manifest_paths = _manifest_paths(addons_root)
    addon_roots = _addon_roots(manifest_paths)
    violations: list[PolicyViolation] = []
    manifests: list[_Manifest] = []
    for path in manifest_paths:
        manifest, errors = _parse_manifest(root, path)
        violations.extend(errors)
        if manifest is not None:
            manifests.append(manifest)

    addon_by_identity: dict[str, Path] = {}
    for manifest in manifests:
        addon_by_identity.setdefault(manifest.identity, manifest.addon_root)
    for manifest in manifests:
        _check_manifest_references(
            root, manifest, addon_by_identity, violations)
    violations.extend(_check_duplicate_identities(root, manifests))

    python_paths = _all_files(addon_roots, ".py")
    violations.extend(_parse_python_files(
        root,
        python_paths,
        exclude={path for path in manifest_paths},
    ))
    violations.extend(_check_python_globals(
        root,
        python_paths,
        exclude={path for path in manifest_paths},
    ))
    xml_paths = _all_files(addon_roots, ".xml")
    violations.extend(_check_xml_files(root, xml_paths))
    violations.extend(_check_duplicate_xml_ids(root, addon_roots, xml_paths))
    csv_paths = _all_files(addon_roots, ".csv")
    for path in csv_paths:
        violations.extend(_check_csv_file(root, path))
    violations.extend(_check_duplicate_acl_ids(root, addon_roots, csv_paths))
    violations.extend(_check_test_discovery(root, addon_roots))

    return sorted(
        violations,
        key=lambda item: (item.path, item.line, item.rule, item.message),
    )


# Public aliases keep the checker easy to discover from focused tests.
find_violations = check_repository
validate_repository = check_repository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="repository root to inspect (default: current directory)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root
    if not repo_root.is_absolute():
        repo_root = Path.cwd() / repo_root
    try:
        violations = check_repository(repo_root)
    except (OSError, ValueError) as exc:
        print(f"v2 static policy: {exc}", file=sys.stderr)
        return 2
    for violation in violations:
        print(violation.format())
    if not violations:
        print(f"v2 static policy: pass ({repo_root.resolve()})")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
