#!/usr/bin/env python3
"""Freeze and compare the V2 repository compatibility surface.

This is a deliberately dependency-free Stage-P00 analyzer.  It never imports
Odoo, opens a database, reads a credential, or contacts Shopify.  Its outputs
are deterministic for a given repository tree and source reference.

The analyzer owns the repository-derived portions of the six V2 baseline
artifacts.  Database and performance files remain explicitly ``pending`` until
their runtime collectors attach measured evidence; absence is never reported as
zero.  Use ``--check`` later to fail on an unexplained compatibility drift.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


SCHEMA_VERSION = 2
CONNECTOR_PREFIX = "shopify_connector_"
OUTPUT_NAMES = (
    "compatibility-baseline.json",
    "database-profile.json",
    "dependency-graph.json",
    "performance-baseline.json",
    "shopify-operation-inventory.json",
    "ui-task-baseline.md",
)
GRAPHQL_OPERATION = re.compile(
    r"^\s*(query|mutation)\b(?:\s+([_A-Za-z][_0-9A-Za-z]*))?",
    re.DOTALL,
)
GRAPHQL_DOCUMENT_START = re.compile(r"^\s*(query|mutation)\b[^\{]*\{")
GRAPHQL_VARIABLE = re.compile(r"\$([_A-Za-z][_0-9A-Za-z]*)\s*:")
SQL_INDEX = re.compile(
    r"CREATE\s+(UNIQUE\s+)?INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
MODEL_ENV_ACCESS = re.compile(
    r"(?:self\.)?env\s*\[\s*['\"]([^'\"]+)['\"]\s*\]"
)


class BaselineError(RuntimeError):
    """A fail-closed analyzer or comparison error."""


def _jsonable(value: Any) -> Any:
    """Return a stable JSON representation for literal manifest values."""
    if isinstance(value, dict):
        return {str(key): _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(_jsonable(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def _literal(node: ast.AST | None, default: Any = None) -> Any:
    if node is None:
        return default
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return default


def _expr(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


_UNRESOLVED = object()


def _resolve_static_value(
    node: ast.AST | None, constants: dict[str, Any]
) -> Any:
    """Resolve a dependency-free module literal, if it is statically known.

    ``ast.literal_eval`` deliberately does not resolve names.  Selection
    declarations in the addons commonly put their literal list in a module
    constant, so resolve names that point at literals while keeping arbitrary
    calls/attributes/operators opaque.  A small amount of sequence/string
    concatenation is safe and useful for constants assembled from literals.
    """
    if node is None:
        return _UNRESOLVED
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        pass
    if isinstance(node, ast.Name):
        return constants.get(node.id, _UNRESOLVED)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_static_value(node.left, constants)
        right = _resolve_static_value(node.right, constants)
        if left is not _UNRESOLVED and right is not _UNRESOLVED:
            try:
                return left + right
            except (TypeError, ValueError):
                return _UNRESOLVED
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_resolve_static_value(item, constants) for item in node.elts]
        if all(value is not _UNRESOLVED for value in values):
            container = {
                ast.List: list,
                ast.Tuple: tuple,
                ast.Set: set,
            }[type(node)]
            try:
                return container(values)
            except (TypeError, ValueError):
                return _UNRESOLVED
    if isinstance(node, ast.Dict):
        keys = [_resolve_static_value(item, constants) for item in node.keys]
        values = [_resolve_static_value(item, constants) for item in node.values]
        if all(item is not _UNRESOLVED for item in keys + values):
            try:
                return dict(zip(keys, values))
            except (TypeError, ValueError):
                return _UNRESOLVED
    return _UNRESOLVED


def _module_literal_constants(tree: ast.Module) -> dict[str, Any]:
    """Collect statically known module-level assignments in source order."""
    constants: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        resolved = _resolve_static_value(value, constants)
        if resolved is _UNRESOLVED:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                constants[target.id] = resolved
    return constants


def _selection_values(value: Any) -> list[str] | None:
    if not isinstance(value, (list, tuple)):
        return None
    values: list[str] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or not item:
            return None
        values.append(str(item[0]))
    return values


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise BaselineError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _is_connector_addon_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    return (
        len(parts) >= 2
        and parts[0] == "addons"
        and parts[1].startswith(CONNECTOR_PREFIX)
    )


def _connector_surface_drift(root: Path, source_sha: str) -> list[str]:
    """Return connector-addon paths differing from the resolved source tree."""
    tracked = _git(
        root,
        "diff",
        "--name-only",
        "--no-renames",
        source_sha,
        "--",
        "addons",
    ).splitlines()
    untracked = _git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "addons",
    ).splitlines()
    return sorted({
        path
        for path in tracked + untracked
        if _is_connector_addon_path(path)
    })


def _assert_connector_surface_matches_source(root: Path, source_sha: str) -> None:
    drift = _connector_surface_drift(root, source_sha)
    if drift:
        raise BaselineError(
            "connector addon working-tree mismatch with source SHA "
            f"{source_sha}: {', '.join(drift)}"
        )


def _connector_addons(root: Path) -> list[Path]:
    return sorted(
        path.parent
        for path in (root / "addons").glob(f"{CONNECTOR_PREFIX}*/__manifest__.py")
    )


def _manifest(addon: Path) -> dict[str, Any]:
    source = (addon / "__manifest__.py").read_text(encoding="utf-8")
    try:
        value = ast.literal_eval(source)
    except (ValueError, SyntaxError) as exc:
        raise BaselineError(f"cannot parse {addon.name}/__manifest__.py: {exc}") from exc
    if not isinstance(value, dict):
        raise BaselineError(f"manifest for {addon.name} is not a dictionary")
    return value


def _field_from_assignment(
    name: str, call: ast.Call, constants: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if not isinstance(call.func.value, ast.Name) or call.func.value.id != "fields":
        return None
    field_type = call.func.attr
    keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
    comodel = _literal(keywords.get("comodel_name"))
    if comodel is None and call.args and field_type in {
        "Many2one", "One2many", "Many2many", "Reference"
    }:
        comodel = _literal(call.args[0])
    compute = _literal(keywords.get("compute")) or _expr(keywords.get("compute"))
    related = _literal(keywords.get("related")) or _expr(keywords.get("related"))
    explicit_store = _literal(keywords.get("store"))
    stored = bool(explicit_store) if explicit_store is not None else not (compute or related)
    selection_node = keywords.get("selection")
    if selection_node is None and call.args and field_type == "Selection":
        selection_node = call.args[0]
    static_constants = constants or {}
    selection = _resolve_static_value(selection_node, static_constants)
    selection_values = _selection_values(selection)
    selection_add_node = keywords.get("selection_add")
    selection_add = _resolve_static_value(selection_add_node, static_constants)
    selection_add_values = _selection_values(selection_add)
    return {
        "name": name,
        "type": field_type,
        "stored": stored,
        "required": bool(_literal(keywords.get("required"), False)),
        "readonly": bool(_literal(keywords.get("readonly"), False)),
        "index": _jsonable(_literal(keywords.get("index"), False)),
        "comodel": comodel,
        "related": related,
        "compute": compute,
        "inverse": _literal(keywords.get("inverse")) or _expr(keywords.get("inverse")),
        "ondelete": _literal(keywords.get("ondelete")),
        "selection_values": selection_values,
        "selection_expression": None if selection_values is not None else _expr(selection_node),
        "selection_add_values": selection_add_values,
        "selection_add_expression": (
            None if selection_add_values is not None else _expr(selection_add_node)
        ),
    }


def _constraint_from_assignment(name: str, call: ast.Call) -> dict[str, Any] | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if not isinstance(call.func.value, ast.Name) or call.func.value.id != "models":
        return None
    if call.func.attr not in {"Constraint", "Index", "UniqueIndex"}:
        return None
    return {
        "name": name,
        "kind": call.func.attr.lower(),
        "arguments": [_jsonable(_literal(arg, _expr(arg))) for arg in call.args],
        "keywords": {
            keyword.arg: _jsonable(_literal(keyword.value, _expr(keyword.value)))
            for keyword in call.keywords
            if keyword.arg
        },
    }


def _decorator_name(node: ast.AST) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    return _expr(target) or ""


def _model_kind(bases: list[str]) -> str:
    """Return the Odoo model family represented by direct class bases."""
    if any(
        base in {"TransientModel", "models.TransientModel"}
        or base.endswith(".TransientModel")
        for base in bases
    ):
        return "transient"
    if any(
        base in {"AbstractModel", "models.AbstractModel"}
        or base.endswith(".AbstractModel")
        for base in bases
    ):
        return "abstract"
    return "model"


def _raw_indexes_from_source(root: Path, path: Path, source: str) -> list[dict[str, Any]]:
    return [
        {
            "name": match.group(2),
            "unique": bool(match.group(1)),
            "source": _relative(root, path),
        }
        for match in SQL_INDEX.finditer(source)
    ]


def _models_from_python(root: Path, addon: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    models: list[dict[str, Any]] = []
    raw_indexes: list[dict[str, Any]] = []
    for path in sorted(addon.rglob("*.py")):
        if "tests" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        raw_indexes.extend(_raw_indexes_from_source(root, path, source))
        if "migrations" in path.parts:
            # Migration scripts are scanned for raw DDL but never inspected as
            # model declarations: they are historical transformations, not
            # registry classes.
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise BaselineError(f"cannot parse {_relative(root, path)}: {exc}") from exc
        constants = _module_literal_constants(tree)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [_expr(base) or "" for base in node.bases]
            if not any(
                base.endswith(("models.Model", "models.AbstractModel", "models.TransientModel"))
                or base.endswith(("Model", "AbstractModel", "TransientModel"))
                for base in bases
            ):
                continue
            attributes: dict[str, ast.AST] = {}
            fields: list[dict[str, Any]] = []
            constraints: list[dict[str, Any]] = []
            public_methods: list[str] = []
            python_constraints: list[dict[str, Any]] = []
            for item in node.body:
                if isinstance(item, (ast.Assign, ast.AnnAssign)):
                    targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                    value = item.value
                    for target in targets:
                        if not isinstance(target, ast.Name) or value is None:
                            continue
                        attributes[target.id] = value
                        if isinstance(value, ast.Call):
                            field = _field_from_assignment(target.id, value, constants)
                            if field:
                                fields.append(field)
                            constraint = _constraint_from_assignment(target.id, value)
                            if constraint:
                                constraints.append(constraint)
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not item.name.startswith("_"):
                        public_methods.append(item.name)
                    decorator_names = [_decorator_name(dec) for dec in item.decorator_list]
                    if "api.constrains" in decorator_names:
                        decorator = next(
                            dec for dec in item.decorator_list
                            if _decorator_name(dec) == "api.constrains"
                        )
                        args = decorator.args if isinstance(decorator, ast.Call) else []
                        python_constraints.append({
                            "method": item.name,
                            "fields": [str(_literal(arg, _expr(arg))) for arg in args],
                        })
            name = _literal(attributes.get("_name"))
            inherit = _literal(attributes.get("_inherit"))
            model_kind = _model_kind(bases)
            table = _literal(attributes.get("_table"))
            # An AbstractModel never owns a PostgreSQL table.  Likewise, an
            # extension class with only _inherit contributes fields/methods to
            # the inherited registry model and must not get a synthetic table
            # from a missing _name.
            if model_kind == "abstract" or not isinstance(name, str):
                table = None
            elif table is None:
                table = name.replace(".", "_")
            sql_constraints = _literal(attributes.get("_sql_constraints"), [])
            if not isinstance(sql_constraints, (list, tuple)):
                sql_constraints = []
            for item in sql_constraints:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    constraints.append({
                        "name": str(item[0]),
                        "kind": "legacy_sql_constraint",
                        "arguments": [_jsonable(value) for value in item[1:]],
                        "keywords": {},
                    })
            models.append({
                "addon": addon.name,
                "class": node.name,
                "source": _relative(root, path),
                "base_kind": bases,
                "model_kind": model_kind,
                "name": name,
                "inherit": _jsonable(inherit),
                "table": table,
                "auto": _literal(attributes.get("_auto"), True),
                "fields": sorted(fields, key=lambda item: item["name"]),
                "constraints": sorted(constraints, key=lambda item: item["name"]),
                "python_constraints": sorted(
                    python_constraints, key=lambda item: item["method"]
                ),
                "public_methods": sorted(set(public_methods)),
            })
    # Keep standalone migration SQL in the same raw-DDL inventory while
    # leaving it out of the Python model pass above.
    for path in sorted(addon.rglob("*.sql")):
        if "tests" in path.parts:
            continue
        raw_indexes.extend(
            _raw_indexes_from_source(root, path, path.read_text(encoding="utf-8"))
        )
    return (
        sorted(models, key=lambda item: (item["source"], item["class"])),
        sorted(raw_indexes, key=lambda item: (item["name"], item["source"])),
    )


def _xml_records(root: Path, addon: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    declared_files = list(manifest.get("data") or []) + list(manifest.get("demo") or [])
    for relative_path in sorted(set(str(item) for item in declared_files)):
        path = addon / relative_path
        if path.suffix.lower() != ".xml" or not path.exists():
            continue
        try:
            tree = ElementTree.parse(path)
        except ElementTree.ParseError as exc:
            raise BaselineError(f"cannot parse {_relative(root, path)}: {exc}") from exc
        for element in tree.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            local_id = element.attrib.get("id")
            if not local_id:
                continue
            model = element.attrib.get("model")
            if tag == "menuitem":
                model = "ir.ui.menu"
            fields: dict[str, Any] = {}
            for field in element:
                if field.tag.rsplit("}", 1)[-1] != "field":
                    continue
                field_name = field.attrib.get("name")
                if not field_name:
                    continue
                fields[field_name] = {
                    key: field.attrib[key]
                    for key in sorted(field.attrib)
                    if key != "name"
                } or (field.text or "").strip()
            records.append({
                "xml_id": f"{addon.name}.{local_id}",
                "local_id": local_id,
                "tag": tag,
                "model": model,
                "source": _relative(root, path),
                "fields": fields,
            })
    return sorted(records, key=lambda item: item["xml_id"])


def _acl_records(root: Path, addon: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative_path in sorted(set(str(item) for item in manifest.get("data") or [])):
        path = addon / relative_path
        if path.suffix.lower() != ".csv" or not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                if not row.get("id"):
                    continue
                records.append({
                    "xml_id": f"{addon.name}.{row['id']}",
                    "model_ref": row.get("model_id:id"),
                    "group_ref": row.get("group_id:id"),
                    "permissions": {
                        key.removeprefix("perm_"): int(row.get(key) or 0)
                        for key in ("perm_read", "perm_write", "perm_create", "perm_unlink")
                    },
                    "source": _relative(root, path),
                })
    return sorted(records, key=lambda item: item["xml_id"])


def _python_edges(
    root: Path, addon_paths: list[Path], *, tests: bool
) -> list[dict[str, str]]:
    addon_names = {path.name for path in addon_paths}
    edges: set[tuple[str, str, str, str]] = set()
    for addon in addon_paths:
        for path in sorted(addon.rglob("*.py")):
            is_test = "tests" in path.parts
            if is_test != tests:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                raise BaselineError(f"cannot parse {_relative(root, path)}: {exc}") from exc
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
                for module in modules:
                    parts = module.split(".")
                    for candidate in addon_names:
                        if candidate in parts and candidate != addon.name:
                            edges.add((addon.name, candidate, _relative(root, path), module))
    return [
        {"from": source, "to": target, "source": path, "import": module}
        for source, target, path, module in sorted(edges)
    ]


def _xml_reference_edges(
    root: Path, addon_paths: list[Path], manifests: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    addon_names = {path.name for path in addon_paths}
    edges: set[tuple[str, str, str, str]] = set()
    reference = re.compile(
        r"\b(" + "|".join(re.escape(name) for name in sorted(addon_names)) + r")\."
    )
    for addon in addon_paths:
        declared = list(manifests[addon.name].get("data") or [])
        for relative_path in sorted(set(str(item) for item in declared)):
            path = addon / relative_path
            if path.suffix.lower() != ".xml" or not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            for match in reference.finditer(source):
                target = match.group(1)
                if target != addon.name:
                    edges.add((addon.name, target, _relative(root, path), match.group(0)))
    return [
        {"from": source, "to": target, "source": path, "reference": value}
        for source, target, path, value in sorted(edges)
    ]


def _cycles(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for source, target in edges:
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
    found: set[tuple[str, ...]] = set()

    def canonical(cycle: list[str]) -> tuple[str, ...]:
        body = cycle[:-1]
        rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
        smallest = min(rotations)
        return smallest + (smallest[0],)

    def visit(node: str, path: list[str], active: set[str]) -> None:
        for target in sorted(adjacency[node]):
            if target in active:
                start = path.index(target)
                found.add(canonical(path[start:] + [target]))
            elif target not in path:
                visit(target, path + [target], active | {target})

    for node in sorted(adjacency):
        visit(node, [node], {node})
    return [list(cycle) for cycle in sorted(found)]


def _graphql_inventory(root: Path, addon_paths: list[Path]) -> dict[str, Any]:
    operations: list[dict[str, Any]] = []
    transport_calls: list[dict[str, Any]] = []
    model_accesses: list[dict[str, Any]] = []
    api_version: str | None = None
    for addon in addon_paths:
        for path in sorted(addon.rglob("*.py")):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                raise BaselineError(f"cannot parse {_relative(root, path)}: {exc}") from exc
            for match in MODEL_ENV_ACCESS.finditer(source):
                if match.group(1) == "shopify.connector.api.client":
                    model_accesses.append({
                        "addon": addon.name,
                        "source": _relative(root, path),
                        "line": source.count("\n", 0, match.start()) + 1,
                    })
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    if value is not None:
                        for target in targets:
                            if isinstance(target, ast.Name) and target.id == "SHOPIFY_API_VERSION":
                                api_version = _literal(value, api_version)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    document = node.value.strip()
                    match = (
                        GRAPHQL_OPERATION.match(document)
                        if GRAPHQL_DOCUMENT_START.match(document)
                        else None
                    )
                    if match and "MutationDispatchSelftest" not in document:
                        digest = _sha256_text(document)
                        declared_name = match.group(2)
                        operations.append({
                            "addon": addon.name,
                            "kind": match.group(1),
                            "name": declared_name,
                            "anonymous": declared_name is None,
                            "inventory_key": declared_name or f"anonymous:{digest[:16]}",
                            "source": _relative(root, path),
                            "line": node.lineno,
                            "sha256": digest,
                            "variables": sorted(set(GRAPHQL_VARIABLE.findall(document))),
                            "has_cursor_variable": "$after" in document,
                            "has_page_info": "pageInfo" in document,
                            "declares_user_errors": "userErrors" in document,
                        })
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in {
                        "execute", "execute_business", "execute_business_read"
                    }:
                        transport_calls.append({
                            "addon": addon.name,
                            "method": node.func.attr,
                            "source": _relative(root, path),
                            "line": node.lineno,
                        })
    operations = sorted(
        operations,
        key=lambda item: (item["inventory_key"], item["source"], item["line"]),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "api_version_literal": api_version,
        "operation_count": len(operations),
        "anonymous_operation_count": sum(item["anonymous"] for item in operations),
        "operations": operations,
        "transport_calls": sorted(
            transport_calls,
            key=lambda item: (item["source"], item["line"], item["method"]),
        ),
        "api_client_model_accesses": sorted(
            model_accesses, key=lambda item: (item["source"], item["line"])
        ),
        "review_contract": {
            "mutation_policy": (
                "Each mutation must be linked manually or by later runtime evidence to "
                "its idempotency, certainty and readback contract; this static inventory "
                "does not infer safety from names."
            ),
            "anonymous_policy": (
                "P00 inventories anonymous documents by digest; P01 must name and own every "
                "operation before its typed registry gate can pass."
            ),
            "version_source": "addons/shopify_connector_core/tools/api_version.py",
            "schema_validator": "tools/validate_shopify_graphql.py",
        },
    }


def _performance_scenarios(root: Path) -> list[str]:
    path = root / "tools" / "perf0_baseline.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "SCENARIOS" for target in node.targets):
                value = _literal(node.value, [])
                if isinstance(value, (list, tuple)):
                    return [str(item) for item in value]
    return []


def _performance_budgets(root: Path) -> list[dict[str, str]]:
    path = root / "docs" / "v2" / "09-test-observability-release-blueprint.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    rows: list[dict[str, str]] = []
    for line in lines:
        if line.startswith("## 7. Performance budgets"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 2 and cells[0] not in {"Operation", "---"}:
            if set(cells[0]) == {"-"}:
                continue
            rows.append({"operation": cells[0], "budget": cells[1]})
    return rows


def _ui_markdown(
    provenance: dict[str, Any], xml_records: list[dict[str, Any]], root: Path
) -> str:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in xml_records:
        by_model[record.get("model") or record["tag"]].append(record)
    js_files = sorted((root / "addons").glob(f"{CONNECTOR_PREFIX}*/static/**/*.js"))
    xml_templates = sorted((root / "addons").glob(f"{CONNECTOR_PREFIX}*/static/**/*.xml"))
    tours: list[tuple[str, str]] = []
    components: list[tuple[str, str]] = []
    for path in js_files:
        source = path.read_text(encoding="utf-8")
        if "tours" in path.parts:
            for match in re.finditer(r"\.add\(\s*['\"]([^'\"]+)", source):
                tours.append((match.group(1), _relative(root, path)))
        for match in re.finditer(r"(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\s+extends\s+Component", source):
            components.append((match.group(1), _relative(root, path)))
    lines = [
        "# V2 UI Task Baseline",
        "",
        "> Repository-derived inventory only. Runtime reachability, rendered states and",
        "> end-to-end completion remain measured evidence and are never inferred here.",
        "",
        "## Provenance",
        "",
        f"- Source ref: `{provenance['source_ref']}`",
        f"- Source SHA: `{provenance['source_sha']}`",
        f"- Generator schema: `{SCHEMA_VERSION}`",
        "",
        "## Inventory counts",
        "",
        "| Surface | Count |",
        "| --- | ---: |",
        f"| Menus | {len(by_model.get('ir.ui.menu', []))} |",
        f"| Window actions | {len(by_model.get('ir.actions.act_window', []))} |",
        f"| Client actions | {len(by_model.get('ir.actions.client', []))} |",
        f"| Views | {len(by_model.get('ir.ui.view', []))} |",
        f"| JavaScript components | {len(set(components))} |",
        f"| Registered tours | {len(set(tours))} |",
        f"| Static XML template files | {len(xml_templates)} |",
        "",
        "## Menus and actions",
        "",
        "| XML ID | Model | Source |",
        "| --- | --- | --- |",
    ]
    for record in sorted(
        by_model.get("ir.ui.menu", [])
        + by_model.get("ir.actions.act_window", [])
        + by_model.get("ir.actions.client", []),
        key=lambda item: item["xml_id"],
    ):
        lines.append(
            f"| `{record['xml_id']}` | `{record['model']}` | `{record['source']}` |"
        )
    lines.extend(["", "## JavaScript components", "", "| Component | Source |", "| --- | --- |"])
    for name, source in sorted(set(components)):
        lines.append(f"| `{name}` | `{source}` |")
    lines.extend(["", "## Registered browser tours", "", "| Tour | Source |", "| --- | --- |"])
    for name, source in sorted(set(tours)):
        lines.append(f"| `{name}` | `{source}` |")
    lines.extend([
        "",
        "## P00 runtime tasks still required",
        "",
        "- Prove every advertised setup and operation entry point is reachable for its role.",
        "- Record loading, empty, blocked, failure, recovery and terminal states in a browser.",
        "- Measure event-to-visible-state latency and active progress feedback.",
        "- Execute U1–U14 on their routed wave; this inventory is not journey evidence.",
        "",
    ])
    return "\n".join(lines)


def build_outputs(root: Path, source_ref: str) -> dict[str, Any]:
    source_sha = _git(root, "rev-parse", f"{source_ref}^{{commit}}")
    _assert_connector_surface_matches_source(root, source_sha)
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "source_ref": source_ref,
        "source_sha": source_sha,
        "generator": "tools/v2_repository_baseline.py",
        "network_access": False,
        "database_access": False,
    }
    addon_paths = _connector_addons(root)
    manifests = {addon.name: _manifest(addon) for addon in addon_paths}
    all_models: list[dict[str, Any]] = []
    raw_indexes: list[dict[str, Any]] = []
    all_xml: list[dict[str, Any]] = []
    all_acl: list[dict[str, Any]] = []
    addon_rows: list[dict[str, Any]] = []
    for addon in addon_paths:
        manifest = manifests[addon.name]
        models, indexes = _models_from_python(root, addon)
        xml_records = _xml_records(root, addon, manifest)
        acl_records = _acl_records(root, addon, manifest)
        all_models.extend(models)
        raw_indexes.extend(indexes)
        all_xml.extend(xml_records)
        all_acl.extend(acl_records)
        addon_rows.append({
            "technical_name": addon.name,
            "version": manifest.get("version"),
            "depends": sorted(str(item) for item in manifest.get("depends") or []),
            "data": [str(item) for item in manifest.get("data") or []],
            "application": bool(manifest.get("application", False)),
            "auto_install": _jsonable(manifest.get("auto_install", False)),
            "installable": bool(manifest.get("installable", True)),
            "uninstall_hook": manifest.get("uninstall_hook"),
        })
    all_xml.sort(key=lambda item: item["xml_id"])
    manifest_edges = [
        {"from": addon, "to": dependency}
        for addon, manifest in sorted(manifests.items())
        for dependency in sorted(str(item) for item in manifest.get("depends") or [])
        if dependency.startswith(CONNECTOR_PREFIX)
    ]
    python_edges = _python_edges(root, addon_paths, tests=False)
    python_test_edges = _python_edges(root, addon_paths, tests=True)
    xml_edges = _xml_reference_edges(root, addon_paths, manifests)
    graph_edges = {(item["from"], item["to"]) for item in manifest_edges}
    graph_edges.update((item["from"], item["to"]) for item in python_edges)
    dependency_graph = {
        **provenance,
        "nodes": sorted(manifests),
        "manifest_edges": manifest_edges,
        "python_cross_addon_imports": python_edges,
        "test_cross_addon_imports": python_test_edges,
        "xml_cross_addon_references": xml_edges,
        "cycles": _cycles(sorted(manifests), sorted(graph_edges)),
    }
    compatibility = {
        **provenance,
        "addons": sorted(addon_rows, key=lambda item: item["technical_name"]),
        "models": sorted(all_models, key=lambda item: (item["source"], item["class"])),
        "xml_records": all_xml,
        "access_controls": sorted(all_acl, key=lambda item: item["xml_id"]),
        "record_rules": [
            item for item in all_xml if item.get("model") == "ir.rule"
        ],
        "cron_records": [
            item for item in all_xml if item.get("model") == "ir.cron"
        ],
        "raw_sql_indexes": sorted(
            raw_indexes, key=lambda item: (item["name"], item["source"])
        ),
        "cross_addon_imports": python_edges,
        "test_cross_addon_imports": python_test_edges,
    }
    database_profile = {
        **provenance,
        "status": "runtime_measurement_pending",
        "absence_semantics": "pending values are not zero and are not acceptance evidence",
        "repository_expectations": {
            "declared_model_classes": len(all_models),
            "declared_tables": sorted(
                {item["table"] for item in all_models if item.get("table") and item.get("auto")}
            ),
            "declared_constraints": sum(len(item["constraints"]) for item in all_models),
            "raw_sql_indexes": sorted({item["name"] for item in raw_indexes}),
        },
        "runtime_required": {
            "environment": None,
            "database_fixture_hash": None,
            "installed_addons_and_versions": None,
            "table_row_counts": None,
            "largest_tables_and_indexes": None,
            "store_binding_job_log_mutation_webhook_counts": None,
            "constraint_and_index_presence": None,
            "backup_restore_identity_samples": None,
            "fresh_and_warm_install_difference": None,
        },
    }
    performance_profile = {
        **provenance,
        "status": "runtime_measurement_pending",
        "absence_semantics": "unmeasured values are null, never zero",
        "existing_perf0_scenarios": _performance_scenarios(root),
        "v2_initial_budgets": _performance_budgets(root),
        "runtime_required": {
            "environment": None,
            "tiny_profile": None,
            "ci_target_profile": None,
            "latency_query_api_cost_memory_lock_results": None,
            "backlog_restart_and_event_to_visible_state": None,
            "command": "tools/perf0_baseline.py -c <odoo.conf> -d <isolated-db> --output <json>",
        },
    }
    operation_inventory = {**provenance, **_graphql_inventory(root, addon_paths)}
    operation_inventory["source_ref"] = source_ref
    operation_inventory["source_sha"] = source_sha
    return {
        "compatibility-baseline.json": compatibility,
        "database-profile.json": database_profile,
        "dependency-graph.json": dependency_graph,
        "performance-baseline.json": performance_profile,
        "shopify-operation-inventory.json": operation_inventory,
        "ui-task-baseline.md": _ui_markdown(provenance, all_xml, root),
    }


def _write_outputs(output_dir: Path, outputs: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_NAMES:
        value = outputs[name]
        # These are machine-readable ledgers and can become large as the
        # connector grows.  Canonical compact JSON keeps Git/PR payloads and
        # evidence transport bounded without dropping any evidence fields.
        # Keep top-level keys on separate lines so provenance-only evidence
        # commits remain reviewable without expanding every nested record.
        if isinstance(value, str):
            content = value
        else:
            items = (
                json.dumps(key, ensure_ascii=False)
                + ":"
                + json.dumps(
                    value[key],
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                for key in sorted(value)
            )
            content = "{\n" + ",\n".join(items) + "\n}\n"
        (output_dir / name).write_text(content, encoding="utf-8")


def _normalized_for_check(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalized_for_check(item)
            for key, item in value.items()
            if key != "source_ref"
        }
    if isinstance(value, list):
        return [_normalized_for_check(item) for item in value]
    return value


def _artifact_source_sha(name: str, value: Any) -> str | None:
    if name.endswith(".json"):
        return value.get("source_sha") if isinstance(value, dict) else None
    match = re.search(r"^- Source SHA: `([^`]+)`$", str(value), re.MULTILINE)
    return match.group(1) if match else None


def _frozen_source_sha(output_dir: Path) -> str:
    """Read the canonical SHA from frozen artifacts for check-mode authority."""
    canonical_path = output_dir / "compatibility-baseline.json"
    if not canonical_path.exists():
        raise BaselineError(f"missing frozen provenance {canonical_path}")
    try:
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BaselineError(f"invalid frozen provenance {canonical_path}: {exc}") from exc
    source_sha = _artifact_source_sha("compatibility-baseline.json", canonical)
    if not source_sha:
        raise BaselineError(f"missing source_sha in frozen provenance {canonical_path}")
    for name in OUTPUT_NAMES:
        path = output_dir / name
        if not path.exists() or name == "compatibility-baseline.json":
            continue
        try:
            value = (
                json.loads(path.read_text(encoding="utf-8"))
                if name.endswith(".json")
                else path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise BaselineError(f"cannot read frozen provenance {path}: {exc}") from exc
        other_sha = _artifact_source_sha(name, value)
        if other_sha and other_sha != source_sha:
            raise BaselineError(
                "frozen source SHA mismatch: "
                f"{canonical_path}={source_sha}, {path}={other_sha}"
            )
    return source_sha


def _check_outputs(output_dir: Path, outputs: dict[str, Any]) -> None:
    failures: list[str] = []
    for name in OUTPUT_NAMES:
        path = output_dir / name
        if not path.exists():
            failures.append(f"missing {path}")
            continue
        if name.endswith(".json"):
            frozen_value = json.loads(path.read_text(encoding="utf-8"))
            regenerated_value = outputs[name]
            frozen_sha = _artifact_source_sha(name, frozen_value)
            regenerated_sha = _artifact_source_sha(name, regenerated_value)
            if frozen_sha != regenerated_sha:
                failures.append(
                    f"source SHA mismatch in {path}: "
                    f"frozen={frozen_sha!r}, regenerated={regenerated_sha!r}"
                )
            expected = _normalized_for_check(frozen_value)
            actual = _normalized_for_check(regenerated_value)
        else:
            expected_text = path.read_text(encoding="utf-8")
            actual_text = str(outputs[name])
            frozen_sha = _artifact_source_sha(name, expected_text)
            regenerated_sha = _artifact_source_sha(name, actual_text)
            if frozen_sha != regenerated_sha:
                failures.append(
                    f"source SHA mismatch in {path}: "
                    f"frozen={frozen_sha!r}, regenerated={regenerated_sha!r}"
                )
            expected = re.sub(
                r"- Source ref: `[^`]+`", r"- Source ref: `<ignored>`", expected_text
            )
            actual = re.sub(
                r"- Source ref: `[^`]+`", r"- Source ref: `<ignored>`", actual_text
            )
        if expected != actual:
            failures.append(f"compatibility drift in {path}")
    if failures:
        raise BaselineError("\n".join(failures))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--source-ref", default="HEAD")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/v2/evidence")
    )
    parser.add_argument(
        "--check", action="store_true", help="compare with existing frozen outputs"
    )
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    try:
        if args.check:
            # The frozen artifact records the code commit C.  A later
            # docs/evidence publication commit is allowed as long as its
            # connector-addon surface is still exactly C.
            frozen_source_sha = _frozen_source_sha(output_dir)
            outputs = build_outputs(root, frozen_source_sha)
            _check_outputs(output_dir, outputs)
            print(f"V2 repository baseline matches {output_dir}.")
        else:
            outputs = build_outputs(root, args.source_ref)
            _write_outputs(output_dir, outputs)
            print(f"Wrote {len(outputs)} V2 baseline artifacts to {output_dir}.")
    except (BaselineError, OSError, json.JSONDecodeError) as exc:
        print(f"v2 repository baseline: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
