"""Static snapshot generator for tests/integration/fixtures/route_dispatch_snapshot.json.

Walks the registry source files and the handler module sources, extracting
(attr_name, ClassName) tuples and ROUTES literals via AST parsing. Builds the
first-match-wins dispatch map for every colliding (method, path) and writes
the JSON fixture.

Standalone — does NOT import aragora, so it works in environments where the
full transitive dependency chain (cryptography, etc.) isn't available. This
makes it suitable for pre-commit hooks and lightweight CI lanes.

Use this when the live HANDLER_REGISTRY isn't importable; the canonical path
is ``UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest tests/integration/test_route_dispatch_behavior.py``,
which uses the live registry and is more accurate when handlers do dynamic
route registration.

Run from the repo root:
    python3 scripts/audit_handler_registry.py
    python3 scripts/audit_handler_registry.py /path/to/checkout

See docs/architecture/HANDLER_REGISTRY_MAP.md for the cluster catalog and
recommended consolidation canonicals.
"""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

REGISTRY_FILES = [
    "aragora/server/handler_registry/admin.py",
    "aragora/server/handler_registry/debates.py",
    "aragora/server/handler_registry/agents.py",
    "aragora/server/handler_registry/analytics.py",
    "aragora/server/handler_registry/memory.py",
    "aragora/server/handler_registry/social.py",
]

# Order matches __init__.py:97-105 — *ADMIN, *DEBATE, *AGENT, *ANALYTICS, *MEMORY, *SOCIAL
COMPOSITION_ORDER = [
    ("ADMIN_HANDLER_REGISTRY", "aragora/server/handler_registry/admin.py"),
    ("DEBATE_HANDLER_REGISTRY", "aragora/server/handler_registry/debates.py"),
    ("AGENT_HANDLER_REGISTRY", "aragora/server/handler_registry/agents.py"),
    ("ANALYTICS_HANDLER_REGISTRY", "aragora/server/handler_registry/analytics.py"),
    ("MEMORY_HANDLER_REGISTRY", "aragora/server/handler_registry/memory.py"),
    ("SOCIAL_HANDLER_REGISTRY", "aragora/server/handler_registry/social.py"),
]


def _string_const(node: ast.expr) -> str | None:
    """Extract a string literal value, or None if the node is dynamic."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_class_name(node: ast.expr) -> str | None:
    """Extract a class name reference from a tuple element."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_registry_tuples(source: str, registry_name: str) -> list[tuple[str, str]]:
    """Parse a registry source file and return [(attr_name, ClassName), ...]
    in literal source order.

    Handles:
      - Plain tuple entries: ("_foo_handler", FooHandler)
      - Conditional inclusions: *([(...)] if X is not None else [])  (treats as included)
      - Star-unpacks: *OTHER_REGISTRY  (these are skipped — they're handled by COMPOSITION_ORDER)
    """
    tree = ast.parse(source)
    target: ast.expr | None = None
    # Walk only top-level statements (tree.body) rather than ast.walk; the
    # registry is a module-level constant by convention, and a function-local
    # assignment to the same name should not match.
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == registry_name:
                    target = node.value
                    break
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == registry_name:
                target = node.value
                break
        if target is not None:
            break

    if target is None or not isinstance(target, (ast.List, ast.Tuple)):
        return []

    out: list[tuple[str, str]] = []
    for elt in target.elts:
        # Plain tuple: ("_foo_handler", FooHandler)
        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
            attr = _string_const(elt.elts[0])
            cls = _extract_class_name(elt.elts[1])
            if attr and cls:
                out.append((attr, cls))
            continue
        # Star-unpack of a conditional list: *([("...", X)] if X else [])
        if isinstance(elt, ast.Starred) and isinstance(elt.value, ast.IfExp):
            body = elt.value.body
            if isinstance(body, ast.List):
                for sub in body.elts:
                    if isinstance(sub, ast.Tuple) and len(sub.elts) == 2:
                        attr = _string_const(sub.elts[0])
                        cls = _extract_class_name(sub.elts[1])
                        if attr and cls:
                            out.append((attr, cls))
            continue
        # Other star unpacks (composition-level) — skip; handled by COMPOSITION_ORDER.
    return out


def _extract_handler_routes(repo_root: Path) -> dict[str, list[str]]:
    """Walk aragora/server/handlers/**/*.py. For each class with a ROUTES attribute,
    record the literal route entries.

    Returns: {ClassName: [normalized "METHOD PATH" entries]}
    """
    handlers_dir = repo_root / "aragora" / "server" / "handlers"
    out: dict[str, list[str]] = {}

    # Sort for deterministic output across filesystems (ext4 vs APFS vs CI
    # containers all return rglob in different orders).
    for py_path in sorted(handlers_dir.rglob("*.py")):
        try:
            source = py_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (UnicodeDecodeError, SyntaxError):
            continue

        # Only top-level classes — nested classes inside functions or other
        # classes are not registered handlers by convention.
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                routes_node: ast.expr | None = None
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "ROUTES":
                            routes_node = stmt.value
                            break
                elif isinstance(stmt, ast.AnnAssign):
                    if isinstance(stmt.target, ast.Name) and stmt.target.id == "ROUTES":
                        routes_node = stmt.value

                if routes_node is None:
                    continue

                routes: list[str] = []
                if isinstance(routes_node, (ast.List, ast.Tuple)):
                    for r in routes_node.elts:
                        s = _string_const(r)
                        if s is not None:
                            routes.append(_normalize(s))
                elif isinstance(routes_node, ast.Dict):
                    for key in routes_node.keys:
                        s = _string_const(key)
                        if s is not None:
                            routes.append(_normalize(s))

                if routes:
                    # Take the first encountered class definition; if a class is defined twice
                    # in the codebase, that's a bug separate from this audit.
                    out.setdefault(node.name, routes)
                break  # Only one ROUTES per class.
    return out


def _normalize(route: str) -> str:
    """Normalize a single ROUTES entry to 'METHOD PATH'."""
    if " " in route:
        method, _, path = route.partition(" ")
        return f"{method.upper()} {path}"
    return f"GET {route}"


def main(repo_root_str: str) -> None:
    repo_root = Path(repo_root_str).resolve()

    # Sentinel check: refuse to operate on a directory that doesn't look like
    # an aragora checkout. The script writes one fixture file under
    # tests/integration/fixtures/, so the worst case of being pointed at the
    # wrong directory is creating that path tree somewhere unexpected. The
    # sentinel narrows the blast radius of a typo'd or hostile path argument.
    sentinel = repo_root / "aragora" / "server" / "handler_registry" / "__init__.py"
    if not sentinel.is_file():
        print(
            f"ERROR: {repo_root} does not look like an aragora checkout "
            f"(missing {sentinel.relative_to(repo_root) if repo_root in sentinel.parents else sentinel}).",
            file=sys.stderr,
        )
        sys.exit(2)

    # 1. Build per-class ROUTES.
    class_routes = _extract_handler_routes(repo_root)

    # 2. Walk registry in composition order.
    first_owner: dict[str, str] = {}
    all_owners: dict[str, list[str]] = defaultdict(list)

    for registry_name, registry_file in COMPOSITION_ORDER:
        path = repo_root / registry_file
        if not path.exists():
            print(f"  WARNING: {registry_file} not found", file=sys.stderr)
            continue
        source = path.read_text(encoding="utf-8")
        entries = _extract_registry_tuples(source, registry_name)
        for attr_name, cls_name in entries:
            routes = class_routes.get(cls_name, [])
            for key in routes:
                all_owners[key].append(attr_name)
                if key not in first_owner:
                    first_owner[key] = attr_name

    # 3. Filter to colliding paths only.
    snapshot = {key: owner for key, owner in first_owner.items() if len(all_owners[key]) > 1}

    # 4. Print summary.
    total_class_routes = sum(len(rs) for rs in class_routes.values())
    n_classes = len(class_routes)
    n_collisions = len(snapshot)
    print(f"Handler classes with ROUTES: {n_classes}", file=sys.stderr)
    print(f"Total route entries across classes: {total_class_routes}", file=sys.stderr)
    print(f"Total unique paths: {len(first_owner)}", file=sys.stderr)
    print(f"Colliding paths: {n_collisions}", file=sys.stderr)

    # 5. Write the fixture.
    fixture_path = repo_root / "tests" / "integration" / "fixtures" / "route_dispatch_snapshot.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    with fixture_path.open("w", encoding="utf-8") as f:
        json.dump(dict(sorted(snapshot.items())), f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Wrote {fixture_path}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
