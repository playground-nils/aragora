"""Lock in the current first-match-wins dispatch outcome for every colliding HTTP path.

When two or more handlers in HANDLER_REGISTRY claim the same (method, path), the
registration order decides which one is invoked. This test snapshots that
decision so consolidation PRs (Waves 4-6 of the foundation-hardening plan) can
prove "the same handler still answers each path" — or, if the answer changes,
flag the change as intentional.

The fixture file at tests/integration/fixtures/route_dispatch_snapshot.json is
the committed expectation. Regenerate by running:

    UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest tests/integration/test_route_dispatch_behavior.py

See docs/architecture/HANDLER_REGISTRY_MAP.md for the cluster catalog and
recommended consolidation canonicals.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "route_dispatch_snapshot.json"
_UPDATE_ENV = "UPDATE_ROUTE_DISPATCH_SNAPSHOT"


def _normalize_route(route: Any) -> tuple[str, str] | None:
    """Extract (method, path) from a ROUTES entry. Returns None if the entry is
    dynamic / not statically parseable.
    """
    if isinstance(route, str):
        if " " in route:
            method, path = route.split(" ", 1)
            return method.upper(), path
        # Path-only string; no method => assume GET (the dispatcher's default for
        # bare path entries; this matches the existing collision test behavior).
        return "GET", route
    if isinstance(route, (tuple, list)):
        if len(route) >= 2:
            return str(route[0]).upper(), str(route[1])
        if len(route) == 1:
            return "GET", str(route[0])
    return None


def _build_dispatch_map() -> dict[str, str]:
    """Walk HANDLER_REGISTRY in registration order. For each (method, path),
    record the first attr_name that claims it.

    Returns: dict mapping "METHOD PATH" -> attr_name (the first owner).
    """
    from aragora.server.handler_registry import HANDLER_REGISTRY
    from aragora.server.handler_registry.core import _DeferredImport

    first_owner: dict[str, str] = {}
    all_owners: dict[str, list[str]] = defaultdict(list)

    for attr_name, handler_ref in HANDLER_REGISTRY:
        if isinstance(handler_ref, _DeferredImport):
            try:
                handler_class = handler_ref.resolve()
            except (ImportError, AttributeError, TypeError) as exc:
                # Narrow except: import-time failures and missing attrs are
                # tolerable (handlers are deferred for a reason). Anything else
                # is a bug we want to surface.
                print(
                    f"WARN: deferred resolution failed for {attr_name}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                continue
        else:
            handler_class = handler_ref

        if handler_class is None:
            continue

        # Use __dict__ rather than getattr so we only see ROUTES declared on
        # this class, not inherited from a parent. The dispatcher operates on
        # the registered class's own surface; counting inherited routes would
        # double-count parent paths and disagree with the AST-based audit
        # script that walks per-class ROUTES literals.
        routes = handler_class.__dict__.get("ROUTES", []) or []
        for route in routes:
            normalized = _normalize_route(route)
            if normalized is None:
                continue
            method, path = normalized
            key = f"{method} {path}"
            all_owners[key].append(attr_name)
            if key not in first_owner:
                first_owner[key] = attr_name

    # Only return entries that are actually colliding — single-owner paths are
    # not behaviorally interesting for this snapshot.
    return {key: owner for key, owner in first_owner.items() if len(all_owners[key]) > 1}


def _load_snapshot() -> dict[str, str]:
    if not FIXTURE_PATH.exists():
        return {}
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_snapshot(snapshot: dict[str, str]) -> None:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIXTURE_PATH.open("w", encoding="utf-8") as f:
        json.dump(dict(sorted(snapshot.items())), f, indent=2, sort_keys=True)
        f.write("\n")


def test_route_dispatch_snapshot() -> None:
    """The first-match-wins handler for every colliding path matches the snapshot.

    If this test fails after a consolidation PR, the consolidation changed which
    handler answers a path. Either:

    1. The change is intentional (e.g. the canonical handler from
       HANDLER_REGISTRY_MAP.md is now answering, the old one was deleted).
       Run ``UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest tests/integration/test_route_dispatch_behavior.py``
       and commit the updated fixture, with
       a note in the PR body explaining which path moved to which handler.

    2. The change is unintentional (registry order changed, a new handler was
       inserted ahead of the canonical). Investigate before updating.
    """
    current = _build_dispatch_map()

    if os.environ.get(_UPDATE_ENV, "").lower() in ("1", "true", "yes"):
        # User explicitly asked to regenerate. Write and pass.
        _save_snapshot(current)
        return

    snapshot = _load_snapshot()

    if not snapshot:
        # No committed fixture. Don't auto-write — test-time disk mutation
        # outside an explicit update mode is a code smell. Fail loudly with
        # instructions, so the human runs the explicit regenerate command.
        pytest.fail(
            f"Snapshot fixture is missing at {FIXTURE_PATH}.\n"
            "Run: UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest "
            "tests/integration/test_route_dispatch_behavior.py\n"
            "Then commit the generated fixture and re-run."
        )

    # Compute drift in both directions for a clear failure message.
    added = {k: current[k] for k in current.keys() - snapshot.keys()}
    removed = {k: snapshot[k] for k in snapshot.keys() - current.keys()}
    changed = {
        k: (snapshot[k], current[k])
        for k in current.keys() & snapshot.keys()
        if current[k] != snapshot[k]
    }

    if not (added or removed or changed):
        return

    lines = ["Route dispatch snapshot drift detected:\n"]
    if changed:
        lines.append(f"  Changed owner ({len(changed)} paths):")
        for key, (was, now) in sorted(changed.items()):
            lines.append(f"    {key}: {was} -> {now}")
    if added:
        lines.append(f"  New colliding paths ({len(added)} added):")
        for key, owner in sorted(added.items()):
            lines.append(f"    {key}: now owned by {owner}")
    if removed:
        lines.append(f"  No-longer-colliding paths ({len(removed)} removed):")
        for key, owner in sorted(removed.items()):
            lines.append(f"    {key}: was owned by {owner}")
    lines.append(
        "\nIf the change is intentional, run "
        "'UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest "
        "tests/integration/test_route_dispatch_behavior.py' "
        "and commit the updated snapshot."
    )

    pytest.fail("\n".join(lines))


def test_dispatch_snapshot_fixture_is_sorted() -> None:
    """The committed fixture should be deterministically ordered for clean diffs.

    If the fixture is missing entirely, ``test_route_dispatch_snapshot`` already
    reports it; this test passes vacuously rather than double-reporting.
    """
    if not FIXTURE_PATH.exists():
        return
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        raw = f.read()
    parsed = json.loads(raw)
    # Re-serialize with the canonical ordering and compare.
    expected = json.dumps(dict(sorted(parsed.items())), indent=2, sort_keys=True) + "\n"
    assert raw == expected, (
        f"{FIXTURE_PATH} is not sorted/normalized. "
        "Run 'UPDATE_ROUTE_DISPATCH_SNAPSHOT=1 pytest "
        "tests/integration/test_route_dispatch_behavior.py' "
        "to regenerate it."
    )
