#!/usr/bin/env python3
"""Classify Metrics Drift enforcement mode for a workflow run.

Pull requests that touch metrics/public-claim sources stay strict. Ordinary
implementation PRs that merely move counted surfaces run advisory so stale
generated counts do not block otherwise-valid work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STRICT_EXACT_PATHS = frozenset(
    {
        ".github/workflows/metrics-drift.yml",
        "docs/CANONICAL_GOALS.md",
        "docs/CAPABILITY_MATRIX.md",
        "docs/COMMERCIAL_OVERVIEW.md",
        "docs/FEATURE_GAP_LIST.md",
        "docs/GA_CHECKLIST.md",
        "docs/HONEST_ASSESSMENT.md",
        "docs/METRICS.md",
        "docs/ROADMAP_30_60_90.md",
        "docs/STATUS.md",
        "docs/status/claims/canonical_metrics.yaml",
        "scripts/check_canonical_metrics.py",
        "scripts/regenerate_metrics.py",
    }
)

STRICT_PREFIXES = ("docs/status/generated/canonical_metrics/",)

COUNTED_EXACT_PATHS = frozenset(
    {
        ".mypy-baseline",
        "docs/api/openapi.json",
    }
)

COUNTED_PREFIXES = (
    "aragora/",
    "sdk/python/aragora_sdk/",
    "sdk/typescript/src/",
    "tests/",
)


def normalize_path(path: str) -> str:
    """Normalize GitHub/Git path output into repo-relative POSIX paths."""
    return path.strip().replace("\\", "/").removeprefix("./")


def load_changed_paths(paths: list[str], changed_files: Path | None) -> list[str]:
    loaded = list(paths)
    if changed_files is not None:
        loaded.extend(changed_files.read_text(encoding="utf-8").splitlines())
    normalized = [normalize_path(path) for path in loaded]
    return [path for path in normalized if path]


def is_strict_path(path: str) -> bool:
    return path in STRICT_EXACT_PATHS or path.startswith(STRICT_PREFIXES)


def is_counted_path(path: str) -> bool:
    return path in COUNTED_EXACT_PATHS or path.startswith(COUNTED_PREFIXES)


def classify(event_name: str, changed_paths: list[str]) -> dict[str, object]:
    """Return a JSON-serializable Metrics Drift enforcement classification."""
    if event_name != "pull_request":
        return {
            "mode": "strict",
            "event_name": event_name,
            "reasons": ["non_pull_request_event"],
            "changed_paths": changed_paths,
            "strict_matches": [],
            "counted_matches": [],
        }

    strict_matches = [path for path in changed_paths if is_strict_path(path)]
    counted_matches = [path for path in changed_paths if is_counted_path(path)]
    if strict_matches:
        return {
            "mode": "strict",
            "event_name": event_name,
            "reasons": ["strict_metrics_or_public_claim_path_changed"],
            "changed_paths": changed_paths,
            "strict_matches": strict_matches,
            "counted_matches": counted_matches,
        }

    reasons = ["pull_request_without_strict_metrics_paths"]
    if not changed_paths:
        reasons.append("no_changed_paths_reported")
    if counted_matches:
        reasons.append("counted_surface_changed")

    return {
        "mode": "advisory",
        "event_name": event_name,
        "reasons": reasons,
        "changed_paths": changed_paths,
        "strict_matches": [],
        "counted_matches": counted_matches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--event-name",
        required=True,
        help="GitHub event name, for example pull_request or workflow_dispatch.",
    )
    parser.add_argument(
        "--changed-files",
        type=Path,
        help="File containing one changed repo-relative path per line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Accepted for explicitness; output is always JSON.",
    )
    parser.add_argument("paths", nargs="*", help="Changed repo-relative paths.")
    args = parser.parse_args(argv)

    changed_paths = load_changed_paths(args.paths, args.changed_files)
    print(json.dumps(classify(args.event_name, changed_paths), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
