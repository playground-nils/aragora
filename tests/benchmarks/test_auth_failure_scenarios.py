"""Tests for docs/benchmarks/auth_failure_scenarios.json — blocked_auth_failure productization.

Confirms each fixture shape maps to the existing TerminalClass.BLOCKED_AUTH_FAILURE
via aragora.swarm.terminal_truth classifiers without spawning real agents or
hitting the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aragora.swarm.terminal_truth import (
    TerminalClass,
    classify_from_metrics,
    classify_preflight_failure,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "docs" / "benchmarks" / "auth_failure_scenarios.json"


def load_fixture() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def fixture() -> dict:
    return load_fixture()


@pytest.fixture(scope="module")
def scenarios(fixture: dict) -> list[dict]:
    return fixture["scenarios"]


# ---------------------------------------------------------------------------
# Fixture shape sanity
# ---------------------------------------------------------------------------


def test_fixture_loads(fixture: dict) -> None:
    assert fixture["schema_version"] == 1
    assert fixture["kind"] == "blocked_auth_failure_scenarios"
    assert fixture["terminal_class"] == "blocked_auth_failure"


def test_every_scenario_has_required_fields(scenarios: list[dict]) -> None:
    required = {"id", "name", "trigger_kind", "expected_terminal_class", "remediation"}
    for s in scenarios:
        missing = required - set(s)
        assert not missing, f"scenario {s.get('id')!r} missing fields: {missing}"


def test_scenario_ids_are_unique(scenarios: list[dict]) -> None:
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids)), f"duplicate scenario ids: {ids}"


def test_scenarios_cover_both_classifier_paths(scenarios: list[dict]) -> None:
    """Both `metrics_row` and `preflight_check` paths must have at least one shape."""
    kinds = {s["trigger_kind"] for s in scenarios}
    assert "preflight_check" in kinds, "no preflight_check scenarios"
    assert "metrics_row" in kinds, "no metrics_row scenarios"


def test_at_least_five_scenarios(scenarios: list[dict]) -> None:
    assert len(scenarios) >= 5, f"need >= 5 canonical shapes, got {len(scenarios)}"


def test_all_expected_classes_are_auth_failure(scenarios: list[dict]) -> None:
    """Every fixture must point at the auth-failure terminal class."""
    for s in scenarios:
        assert s["expected_terminal_class"] == TerminalClass.BLOCKED_AUTH_FAILURE.value, (
            f"scenario {s['id']} points at {s['expected_terminal_class']!r}, "
            f"not the auth-failure class"
        )


# ---------------------------------------------------------------------------
# Classifier round-trip per scenario
# ---------------------------------------------------------------------------


def test_preflight_scenarios_classify_to_auth_failure(scenarios: list[dict]) -> None:
    preflight_scenarios = [s for s in scenarios if s["trigger_kind"] == "preflight_check"]
    assert preflight_scenarios, "expected at least one preflight scenario"
    for s in preflight_scenarios:
        preflight = s["preflight_check"]
        result = classify_preflight_failure(
            passed=bool(preflight.get("passed", False)),
            checks=list(preflight.get("checks", [])),
            dispatch_gate=preflight.get("dispatch_gate"),
        )
        assert result == TerminalClass.BLOCKED_AUTH_FAILURE, (
            f"scenario {s['id']} preflight classified as {result!r}, expected BLOCKED_AUTH_FAILURE"
        )


def test_metrics_row_scenarios_classify_to_auth_failure(scenarios: list[dict]) -> None:
    metrics_scenarios = [s for s in scenarios if s["trigger_kind"] == "metrics_row"]
    assert metrics_scenarios, "expected at least one metrics_row scenario"
    for s in metrics_scenarios:
        result = classify_from_metrics(dict(s["metrics_row"]))
        assert result == TerminalClass.BLOCKED_AUTH_FAILURE, (
            f"scenario {s['id']} metrics row classified as {result!r}, "
            "expected BLOCKED_AUTH_FAILURE"
        )


def test_each_expected_hint_appears_in_preflight_detail(scenarios: list[dict]) -> None:
    """Sanity check: the `expected_triggered_hints` are actually present in the preflight detail."""
    for s in scenarios:
        if s["trigger_kind"] != "preflight_check":
            continue
        hints = [str(h).lower() for h in s.get("expected_triggered_hints", [])]
        details_blob = " ".join(
            str(check.get("detail", "")).lower() for check in s["preflight_check"].get("checks", [])
        )
        names_blob = " ".join(
            str(check.get("name", "")).lower() for check in s["preflight_check"].get("checks", [])
        )
        for hint in hints:
            assert hint in details_blob or hint in names_blob, (
                f"scenario {s['id']} claims hint {hint!r} but it's not in "
                "preflight check name/detail"
            )


# ---------------------------------------------------------------------------
# Discipline: no live network / agent spawning
# ---------------------------------------------------------------------------


def test_fixture_contains_no_secrets() -> None:
    """The fixture must not embed any real secret-shaped strings."""
    text = FIXTURE_PATH.read_text(encoding="utf-8").lower()
    forbidden_substrings = [
        "sk-proj-",
        "sk-ant-",
        "ghp_",
        "ghs_",
        "gho_",
        "github_pat_",
        "akia",
        "bearer ey",
    ]
    for needle in forbidden_substrings:
        assert needle not in text, f"fixture contains forbidden substring {needle!r}"
