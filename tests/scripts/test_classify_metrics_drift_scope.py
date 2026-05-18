from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "classify_metrics_drift_scope.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("classify_metrics_drift_scope", str(SCRIPT))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["classify_metrics_drift_scope"] = module
    spec.loader.exec_module(module)
    return module


def test_non_pull_request_events_are_strict():
    mod = _load_module()

    result = mod.classify("workflow_dispatch", [])

    assert result["mode"] == "strict"
    assert result["reasons"] == ["non_pull_request_event"]


def test_public_claim_and_metrics_source_paths_are_strict():
    mod = _load_module()

    result = mod.classify(
        "pull_request",
        [
            "aragora/example.py",
            "docs/CANONICAL_GOALS.md",
            "scripts/regenerate_metrics.py",
        ],
    )

    assert result["mode"] == "strict"
    assert result["strict_matches"] == [
        "docs/CANONICAL_GOALS.md",
        "scripts/regenerate_metrics.py",
    ]
    assert result["counted_matches"] == ["aragora/example.py"]


def test_ordinary_counted_surface_prs_are_advisory():
    mod = _load_module()

    result = mod.classify(
        "pull_request",
        [
            "tests/scripts/test_example.py",
            "sdk/python/aragora_sdk/client.py",
            "docs/api/openapi.json",
            ".mypy-baseline",
        ],
    )

    assert result["mode"] == "advisory"
    assert "counted_surface_changed" in result["reasons"]
    assert result["strict_matches"] == []


def test_empty_pull_request_path_list_is_advisory():
    mod = _load_module()

    result = mod.classify("pull_request", [])

    assert result["mode"] == "advisory"
    assert "no_changed_paths_reported" in result["reasons"]


def test_unknown_pull_request_paths_are_advisory_not_strict():
    mod = _load_module()

    result = mod.classify("pull_request", ["docs/random-note.md"])

    assert result["mode"] == "advisory"
    assert result["strict_matches"] == []
    assert result["counted_matches"] == []
