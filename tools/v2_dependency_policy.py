#!/usr/bin/env python3
"""Fail-closed dependency checks for the inert V2 package skeleton.

The checker is intentionally AST-only and dependency-free.  It checks the new
layer directories without importing Odoo or executing application code.  The
legacy ``models`` tree is not scanned until a later migration work item moves
code behind these boundaries.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


LAYER_NAMES = {"application", "domain", "runtime", "integration"}
ALLOWED_IMPORTS = {
    # Domain policies are pure and may only use other domain contracts.
    "domain": {"domain"},
    # Application may depend on domain and explicit runtime ports, but not on
    # a Shopify adapter or presentation layer.
    "application": {"application", "domain", "runtime"},
    # Runtime coordinates application/domain contracts and integration ports.
    "runtime": {"runtime", "application", "domain", "integration"},
    # The Shopify adapter may normalize domain values but cannot reach back up.
    # ``tools`` is an explicitly reviewed, pure support namespace in the
    # core addon (API-version and redaction helpers).  It is not an
    # architectural layer and is available only to the Shopify adapter.
    "integration": {"integration", "domain", "tools"},
}

# These imports either perform network I/O themselves or expose a direct
# network client.  ``urllib.parse`` is deliberately not included; importing a
# parser is not a transport boundary.  New transports must live under
# integration/shopify and be reviewed there.
NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "boto3",
    "ftplib",
    "http",
    "httpx",
    "requests",
    "socket",
    "telnetlib",
    "urllib",
    "websocket",
    "xmlrpc",
}
NETWORK_CALL_NAMES = {
    "create_connection",
    "create_server",
    "getaddrinfo",
    "urlopen",
    "urlretrieve",
}
NETWORK_ATTRIBUTE_NAMES = {
    "connect",
    "delete",
    "get",
    "post",
    "put",
    "request",
    "send",
    "urlopen",
}

# The P01 packages are deliberately pure.  Odoo model/framework imports belong
# to the compatibility/application adapter layer, not to domain/runtime
# contracts.  Keeping this separate from the network list makes the policy
# failure explicit to authors.
ODOO_IMPORT_ROOTS = {"odoo"}
# Other addons are loaded through Odoo's canonical namespace in a deployed
# registry.  These are the reviewed, pure core contracts that domain adapters
# may consume; a broad ``odoo.addons`` exemption would hide real framework
# imports and is intentionally not allowed.
ALLOWED_PURE_CONTRACT_IMPORT_PREFIXES = frozenset((
    "odoo.addons.shopify_connector_core.domain",
    "odoo.addons.shopify_connector_core.integration.shopify",
))

# A malformed or generated package must not make a static gate recurse forever
# or consume unbounded memory.  The actual P01 package is far below these
# limits; exceeding them is itself a policy failure that requires review.
MAX_CYCLE_NODES = 512
MAX_CYCLE_EDGES = 4096


@dataclass(frozen=True, slots=True)
class DependencyViolation:
    path: str
    line: int
    rule: str
    message: str
    import_name: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _layer(relative: Path) -> str | None:
    """Return the architectural layer for a path below the package root."""

    parts = relative.parts
    if not parts or parts[0] not in LAYER_NAMES:
        return None
    # ``integration/shopify`` is the only integration subtree in P01.  The
    # marker ``integration/__init__.py`` is not itself a transport boundary.
    if parts[0] == "integration":
        return "integration" if len(parts) > 1 and parts[1] == "shopify" else None
    return parts[0]


def _module_name(path: Path, root: Path) -> tuple[str, str | None, str]:
    relative = path.relative_to(root)
    module_parts = list(relative.with_suffix("").parts)
    if module_parts and module_parts[-1] == "__init__":
        module_parts.pop()
    package_name = root.name
    module = ".".join([package_name, *module_parts])
    current_package = ".".join([package_name, *module_parts])
    if relative.name != "__init__.py":
        current_package = ".".join([package_name, *module_parts[:-1]])
    return module, current_package, _layer(relative) or ""


def _resolve_import(
    module: str | None,
    level: int,
    current_package: str,
) -> str | None:
    if level == 0:
        return module
    parts = current_package.split(".")
    # level=1 means the current package; level=2 means its parent.
    keep = len(parts) - level + 1
    if keep < 1:
        return None
    prefix = parts[:keep]
    if module:
        prefix.extend(module.split("."))
    return ".".join(prefix)


def _normalise_internal(module: str | None, package_name: str) -> str | None:
    if not module:
        return None
    aliases = (package_name, f"addons.{package_name}")
    for prefix in aliases:
        if module == prefix:
            return prefix
        if module.startswith(prefix + "."):
            return package_name + module[len(prefix):]
    return None


def _internal_layer(module: str | None) -> str | None:
    """Return a known layer for a normalized package module."""

    if not module:
        return None
    parts = module.split(".")
    if len(parts) < 2:
        return None
    if parts[1] == "integration":
        return "integration" if len(parts) > 2 and parts[2] == "shopify" else None
    if parts[1] == "tools":
        return "tools"
    return parts[1] if parts[1] in {"application", "domain", "runtime"} else None


def _is_internal_module(module: str | None, package_name: str) -> bool:
    """Whether a normalized import points into this addon package."""

    return bool(module and (module == package_name or module.startswith(package_name + ".")))


def _is_odoo_module(module: str | None) -> bool:
    return bool(module and (module == "odoo" or module.startswith("odoo.")))


def _is_integration_module(module: str | None) -> bool:
    """Whether an import names an integration boundary module."""

    return bool(module and "integration" in module.split("."))


def _is_allowed_pure_contract_import(module: str | None) -> bool:
    return bool(module and any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in ALLOWED_PURE_CONTRACT_IMPORT_PREFIXES
    ))


def _internal_import_targets(
    node: ast.Import | ast.ImportFrom,
    resolved: str | None,
    package_name: str,
) -> tuple[str, ...]:
    """Return all internal modules touched by an import statement.

    For ``from package.layer import name`` both the package module and the
    named child are candidates.  The package candidate catches a forbidden
    import even when the child is not present in the fixture tree; the child
    candidate lets the cycle graph resolve the actual module when it is.
    """

    candidates: list[str] = []
    if isinstance(node, ast.Import):
        candidates.extend(alias.name for alias in node.names)
    elif resolved:
        candidates.append(resolved)
        for alias in node.names:
            if alias.name != "*":
                candidates.append(f"{resolved}.{alias.name}")
    normalised = []
    for candidate in candidates:
        internal = _normalise_internal(candidate, package_name)
        if internal and internal not in normalised:
            normalised.append(internal)
    return tuple(normalised)


def _module_edges(
    path: Path,
    tree: ast.AST,
    root: Path,
    package_name: str,
    module_names: dict[str, tuple[Path, str]],
) -> list[tuple[str, Path, int]]:
    """Resolve bounded same-layer import edges for one parsed module."""

    _, current_package, source_layer = _module_name(path, root)
    if current_package is None:
        return []
    source_module, _, _ = _module_name(path, root)
    edges: list[tuple[str, Path, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            resolved = None
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import(node.module, node.level, current_package)
        else:
            continue
        for candidate in _internal_import_targets(node, resolved, package_name):
            target = module_names.get(candidate)
            if target is None:
                continue
            target_path, target_layer = target
            if target_layer == source_layer:
                edges.append((candidate, target_path, node.lineno))
    return edges


def _same_layer_cycles(
    graph: dict[str, list[tuple[str, Path, int]]],
) -> tuple[tuple[str, ...], ...]:
    """Return deterministic strongly connected components with cycles."""

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target, _path, _line in graph.get(node, ()):
            if target not in indices:
                visit(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])
        if lowlink[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            current = stack.pop()
            on_stack.remove(current)
            component.append(current)
            if current == node:
                break
        if len(component) > 1 or any(
            target == node for target, _path, _line in graph.get(node, ())
        ):
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return tuple(sorted(components))


def _network_root(module: str) -> str | None:
    if module == "urllib.parse" or module.startswith("urllib.parse."):
        return None
    root = module.split(".", 1)[0]
    return root if root in NETWORK_IMPORT_ROOTS else None


def _violation(
    path: Path,
    root: Path,
    line: int,
    rule: str,
    message: str,
    import_name: str | None = None,
) -> DependencyViolation:
    return DependencyViolation(
        path=path.relative_to(root).as_posix(),
        line=line,
        rule=rule,
        message=message,
        import_name=import_name,
    )


def check_package(package_root: Path) -> list[DependencyViolation]:
    """Return deterministic violations for the new V2 package directories."""

    root = package_root.resolve()
    if not root.is_dir():
        raise ValueError(f"package root is not a directory: {root}")
    package_name = root.name
    violations: list[DependencyViolation] = []
    parsed: dict[Path, tuple[ast.AST, str, str, str]] = {}
    module_names: dict[str, tuple[Path, str]] = {}
    layer_paths = [
        path for path in sorted(root.rglob("*.py")) if _layer(path.relative_to(root))
    ]
    if len(layer_paths) > MAX_CYCLE_NODES:
        path = layer_paths[MAX_CYCLE_NODES]
        violations.append(_violation(
            path,
            root,
            1,
            "cycle-analysis-limit",
            f"same-layer cycle analysis is limited to {MAX_CYCLE_NODES} modules",
        ))
        layer_paths = layer_paths[:MAX_CYCLE_NODES]

    for path in layer_paths:
        relative = path.relative_to(root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            violations.append(_violation(
                path,
                root,
                getattr(exc, "lineno", 1) or 1,
                "syntax",
                f"cannot parse source: {exc}",
            ))
            continue
        module, current_package, source_layer = _module_name(path, root)
        if current_package is None:
            continue
        # Keep the package context with the parse result.  Import resolution
        # is file-local; using the last parsed file's context would silently
        # rewrite every relative import to that unrelated layer.
        parsed[path] = (tree, module, source_layer, current_package or "")
        module_names[module] = (path, source_layer)

    for path in layer_paths:
        parsed_entry = parsed.get(path)
        if parsed_entry is None:
            continue
        tree, _module, source_layer, current_package = parsed_entry
        network_aliases: set[str] = set()
        network_call_aliases: set[str] = set()
        seen: set[tuple[str, int, str, str | None]] = set()

        def add(
            line: int,
            rule: str,
            message: str,
            import_name: str | None = None,
        ) -> None:
            marker = (rule, line, message, import_name)
            if marker not in seen:
                seen.add(marker)
                violations.append(_violation(path, root, line, rule, message, import_name))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    if (
                        _is_odoo_module(imported)
                        and not _is_allowed_pure_contract_import(imported)
                    ):
                        add(
                            node.lineno,
                            "framework-import",
                            f"Odoo import {imported!r} is forbidden in P01 layers",
                            imported,
                        )
                    network = _network_root(imported)
                    if network:
                        local_name = alias.asname or imported.split(".", 1)[0]
                        network_aliases.add(local_name)
                        if imported.rsplit(".", 1)[-1] in NETWORK_CALL_NAMES | NETWORK_ATTRIBUTE_NAMES:
                            network_call_aliases.add(local_name)
                        if source_layer != "integration":
                            add(
                                node.lineno,
                                "direct-network",
                                f"direct network import {imported!r} is outside integration/shopify",
                                imported,
                            )
                    internal = _normalise_internal(imported, package_name)
                    if source_layer == "application" and _is_integration_module(imported):
                        add(
                            node.lineno,
                            "application-integration-import",
                            f"application may not import integration module {imported!r}; use an application-owned port",
                            imported,
                        )
                    if internal and _internal_layer(internal) is None:
                        add(
                            node.lineno,
                            "forbidden-internal-import",
                            f"{source_layer} may not import internal module {imported!r}",
                            imported,
                        )
                    elif internal:
                        target_layer = _internal_layer(internal)
                        if target_layer not in ALLOWED_IMPORTS[source_layer]:
                            add(
                                node.lineno,
                                "reverse-import",
                                f"{source_layer} may not import {target_layer}",
                                imported,
                            )
            elif isinstance(node, ast.ImportFrom):
                raw_module = node.module
                resolved = _resolve_import(raw_module, node.level, current_package)
                imported_for_network = raw_module or resolved or ""
                if (
                    node.level == 0
                    and _is_odoo_module(raw_module)
                    and not _is_allowed_pure_contract_import(raw_module)
                ):
                    add(
                        node.lineno,
                        "framework-import",
                        f"Odoo import {raw_module!r} is forbidden in P01 layers",
                        raw_module,
                    )
                network = _network_root(imported_for_network) if node.level == 0 else None
                if network:
                    for alias in node.names:
                        local_name = alias.asname or alias.name
                        network_aliases.add(local_name)
                        if alias.name in NETWORK_CALL_NAMES | NETWORK_ATTRIBUTE_NAMES:
                            network_call_aliases.add(local_name)
                    if source_layer != "integration":
                        add(
                            node.lineno,
                            "direct-network",
                            f"direct network import {imported_for_network!r} is outside integration/shopify",
                            imported_for_network,
                        )
                internal = _normalise_internal(resolved, package_name)
                if source_layer == "application" and _is_integration_module(resolved or raw_module):
                    add(
                        node.lineno,
                        "application-integration-import",
                        f"application may not import integration module {(resolved or raw_module)!r}; use an application-owned port",
                        resolved or raw_module,
                    )
                internal_candidates = _internal_import_targets(node, resolved, package_name)
                for candidate in internal_candidates:
                    if _internal_layer(candidate) is None:
                        add(
                            node.lineno,
                            "forbidden-internal-import",
                            f"{source_layer} may not import internal module {candidate!r}",
                            candidate,
                        )
                    else:
                        target_layer = _internal_layer(candidate)
                        if target_layer not in ALLOWED_IMPORTS[source_layer]:
                            add(
                                node.lineno,
                                "reverse-import",
                                f"{source_layer} may not import {target_layer}",
                                candidate,
                            )
                # The resolved package is retained for compatibility with
                # imports whose aliases are not concrete child modules (for
                # example ``from package.domain import *``).
                if internal and not internal_candidates:
                    target_layer = _internal_layer(internal)
                    if target_layer is None:
                        add(
                            node.lineno,
                            "forbidden-internal-import",
                            f"{source_layer} may not import internal module {resolved!r}",
                            resolved,
                        )
                    elif target_layer not in ALLOWED_IMPORTS[source_layer]:
                        add(
                            node.lineno,
                            "reverse-import",
                            f"{source_layer} may not import {target_layer}",
                            resolved,
                        )
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name) and (
                    function.id in NETWORK_CALL_NAMES or function.id in network_call_aliases
                ):
                    if source_layer != "integration":
                        add(
                            node.lineno,
                            "direct-network",
                            f"direct network call {function.id!r} is outside integration/shopify",
                            function.id,
                        )
                elif isinstance(function, ast.Attribute):
                    if (
                        isinstance(function.value, ast.Name)
                        and function.value.id in network_aliases
                        and function.attr in NETWORK_ATTRIBUTE_NAMES
                        and source_layer != "integration"
                    ):
                        add(
                            node.lineno,
                            "direct-network",
                            f"direct network call {function.value.id}.{function.attr} is outside integration/shopify",
                            f"{function.value.id}.{function.attr}",
                        )

    graph: dict[str, list[tuple[str, Path, int]]] = {}
    edge_count = 0
    for path, (tree, module, _source_layer, _current_package) in parsed.items():
        edges = _module_edges(path, tree, root, package_name, module_names)
        edge_count += len(edges)
        if edge_count > MAX_CYCLE_EDGES:
            violations.append(_violation(
                path,
                root,
                1,
                "cycle-analysis-limit",
                f"same-layer cycle analysis is limited to {MAX_CYCLE_EDGES} edges",
            ))
            break
        graph[module] = edges
    if edge_count <= MAX_CYCLE_EDGES:
        for component in _same_layer_cycles(graph):
            names = " -> ".join(component)
            component_set = set(component)
            for source in component:
                for target, target_path, line in graph.get(source, ()):
                    if target in component_set:
                        violations.append(_violation(
                            module_names[source][0],
                            root,
                            line,
                            "same-layer-cycle",
                            f"same-layer import cycle: {names}",
                            target,
                        ))

    return sorted(
        violations,
        key=lambda item: (item.path, item.line, item.rule, item.message, item.import_name or ""),
    )


# Public aliases make the checker easy to call from a boundary test without
# requiring callers to know the CLI function name.
check_dependencies = check_package
find_violations = check_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-root",
        "--root",
        type=Path,
        default=Path("addons/shopify_connector_core"),
        help="new V2 package root to inspect",
    )
    parser.add_argument("--json", action="store_true", help="emit violations as JSON")
    args = parser.parse_args(argv)
    root = args.package_root
    if not root.is_absolute():
        root = Path.cwd() / root
    try:
        violations = check_package(root)
    except (OSError, ValueError) as exc:
        print(f"v2 dependency policy: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([item.as_dict() for item in violations], indent=2, sort_keys=True))
    elif violations:
        for item in violations:
            print(f"{item.path}:{item.line}: {item.rule}: {item.message}")
    else:
        print(f"v2 dependency policy: pass ({root})")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
