"""
Route dispatch snapshot test.

Locks in the current "first registered owner wins" dispatch behavior for
every cross-handler colliding path. Consolidation PRs (Waves 4-6 of the
foundation-hardening roadmap) must not silently change which handler answers
a colliding path.

How to use this test in a consolidation PR:

1. Make your handler consolidation changes (e.g. delete a duplicate handler
   module, move methods into a canonical handler).

2. Run this test. If it FAILS for paths you intentionally moved, regenerate
   the snapshot:

       python -c '
       import json
       from collections import defaultdict
       from aragora.server.handler_registry import HANDLER_REGISTRY
       from aragora.server.handler_registry.core import _DeferredImport
       route_owners = defaultdict(list)
       for attr_name, handler_ref in HANDLER_REGISTRY:
           handler_class = (
               handler_ref.resolve() if isinstance(handler_ref, _DeferredImport)
               else handler_ref
           )
           if handler_class is None:
               continue
           routes = getattr(handler_class, "ROUTES", [])
           if isinstance(routes, dict):
               for path in routes.keys():
                   if attr_name not in route_owners[path]:
                       route_owners[path].append(attr_name)
           elif isinstance(routes, list):
               for route in routes:
                   if isinstance(route, str):
                       path = route.split(" ", 1)[-1] if " " in route else route
                   elif isinstance(route, (tuple, list)):
                       path = route[1] if len(route) >= 2 else route[0]
                   else:
                       continue
                   if attr_name not in route_owners[path]:
                       route_owners[path].append(attr_name)
       collisions = {p: o for p, o in route_owners.items() if len(o) > 1}
       snapshot = {
           "_meta": {
               "description": "Locked-in dispatch winners for cross-handler colliding paths.",
               "generated_at": "<TODAY>",
               "rule": "First handler registered in HANDLER_REGISTRY wins.",
               "purpose": "Consolidation PRs must not silently change dispatch winners.",
               "total_collisions": len(collisions),
           },
           "winners": {p: o[0] for p, o in sorted(collisions.items())},
       }
       json.dump(snapshot, open("tests/integration/_snapshots/route_dispatch_snapshot.json", "w"), indent=2)
       '

3. Diff the snapshot file. Every changed entry should correspond to an
   intentional consolidation in your PR. If an unintended change appears,
   investigate before regenerating.

4. Commit the regenerated snapshot WITH your consolidation PR. The PR
   description should call out which winners changed and why.

The bound-counting test in test_handler_registry_imports.py tracks the
TOTAL collision count and ratchets downward as cleanups land. THIS test
locks in the per-path winner so we don't accidentally swap who answers
when paths still collide.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

SNAPSHOT_PATH = Path(__file__).parent / "_snapshots" / "route_dispatch_snapshot.json"


def _build_route_owners() -> dict[str, list[str]]:
    """Replicate the dispatch-resolution logic: for every path, list owners
    in registration order. The first owner wins (per
    ``RouteIndex._exact_routes`` build: ``if path not in self._exact_routes``).
    """
    from aragora.server.handler_registry import HANDLER_REGISTRY
    from aragora.server.handler_registry.core import _DeferredImport

    route_owners: dict[str, list[str]] = defaultdict(list)
    for attr_name, handler_ref in HANDLER_REGISTRY:
        if isinstance(handler_ref, _DeferredImport):
            handler_class = handler_ref.resolve()
        else:
            handler_class = handler_ref
        if handler_class is None:
            continue
        routes = getattr(handler_class, "ROUTES", [])
        if isinstance(routes, dict):
            for path in routes.keys():
                if attr_name not in route_owners[path]:
                    route_owners[path].append(attr_name)
        elif isinstance(routes, list):
            for route in routes:
                if isinstance(route, str):
                    path = route.split(" ", 1)[-1] if " " in route else route
                elif isinstance(route, (tuple, list)):
                    path = route[1] if len(route) >= 2 else route[0]
                else:
                    continue
                if attr_name not in route_owners[path]:
                    route_owners[path].append(attr_name)
    return dict(route_owners)


@pytest.fixture(scope="module")
def snapshot() -> dict:
    """Load the snapshot of expected dispatch winners."""
    assert SNAPSHOT_PATH.exists(), (
        f"Route dispatch snapshot not found at {SNAPSHOT_PATH}. "
        "Generate it via the procedure in this module's docstring."
    )
    return json.loads(SNAPSHOT_PATH.read_text())


@pytest.fixture(scope="module")
def current_winners() -> dict[str, str]:
    """Compute current dispatch winners for every colliding path."""
    route_owners = _build_route_owners()
    collisions = {p: o for p, o in route_owners.items() if len(o) > 1}
    return {p: o[0] for p, o in sorted(collisions.items())}


class TestRouteDispatchSnapshot:
    """Lock in the dispatch winner for every colliding path."""

    def test_snapshot_is_present_and_valid(self, snapshot):
        assert "_meta" in snapshot
        assert "winners" in snapshot
        assert isinstance(snapshot["winners"], dict)
        assert snapshot["_meta"].get("total_collisions") == len(snapshot["winners"]), (
            "Snapshot _meta.total_collisions disagrees with len(winners)"
        )

    def test_no_dispatch_winner_silently_changed(self, snapshot, current_winners):
        """For every colliding path that was in the snapshot, the same
        handler must still be the dispatch winner today.

        If a winner CHANGED, your consolidation PR has done something
        more than handler renaming — it has shifted dispatch behavior.
        Investigate, then regenerate the snapshot deliberately.
        """
        changed = []
        for path, expected_winner in snapshot["winners"].items():
            actual_winner = current_winners.get(path)
            if actual_winner is None:
                # Path no longer collides (a consolidation removed all but one
                # owner). That's allowed — the bound-counting test will
                # observe the reduced collision count.
                continue
            if actual_winner != expected_winner:
                changed.append((path, expected_winner, actual_winner))

        if changed:
            msg = "\n".join(
                f"  {path}: snapshot={exp!r}, current={act!r}" for path, exp, act in changed
            )
            pytest.fail(
                f"{len(changed)} colliding path(s) had their dispatch winner change "
                f"silently. Either revert the change or regenerate the snapshot "
                f"intentionally (see this module's docstring):\n{msg}"
            )

    def test_no_new_collisions_introduced(self, snapshot, current_winners):
        """If a path WAS NOT colliding before but IS colliding now, that's a
        new accidental collision. The bound test will also catch this, but
        this test surfaces the specific paths.
        """
        new_colliding = sorted(set(current_winners) - set(snapshot["winners"]))
        if new_colliding:
            msg = "\n".join(f"  - {p}" for p in new_colliding)
            pytest.fail(
                f"{len(new_colliding)} new colliding path(s) detected. Either "
                f"the new owner is intentional (regenerate the snapshot) or "
                f"the new registration is a bug:\n{msg}"
            )
