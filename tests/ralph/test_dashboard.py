"""Tests for Ralph orchestration observability dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from aragora.ralph.dashboard import (
    load_blocker_history,
    load_dashboard_summary,
    load_project_lifecycle,
)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _make_state(
    *,
    campaign_id: str = "camp-1",
    status: str = "running",
    current_step: int = 10,
    budget_spent_usd: float = 2.5,
    active_blocker: str | None = None,
    blocker_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "supervisor_id": "sup-1",
        "campaign_id": campaign_id,
        "status": status,
        "current_step": current_step,
        "budget_spent_usd": budget_spent_usd,
        "blocker_history": blocker_history or [],
    }
    if active_blocker is not None:
        state["active_blocker"] = active_blocker
    return state


def _make_manifest(
    *,
    campaign_id: str = "camp-1",
    budget_limit_usd: float = 50.0,
    projects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "created_at": "2026-03-18T00:00:00Z",
        "source_kind": "issue",
        "source_ref": "#1007",
        "budget_limit_usd": budget_limit_usd,
        "projects": projects or [],
    }


# ---------------------------------------------------------------------------
# test_summary_basic
# ---------------------------------------------------------------------------


def test_summary_basic(tmp_path: Path) -> None:
    state_path = tmp_path / "state.yaml"
    manifest_path = tmp_path / "manifest.yaml"

    _write_yaml(state_path, _make_state(current_step=10, budget_spent_usd=2.5))
    _write_yaml(
        manifest_path,
        _make_manifest(
            projects=[
                {"project_id": "p1", "title": "A", "status": "completed"},
                {"project_id": "p2", "title": "B", "status": "active"},
            ]
        ),
    )

    result = load_dashboard_summary(state_path, manifest_path)

    assert result["found"] is True
    assert result["campaign_id"] == "camp-1"
    assert result["status"] == "running"
    assert result["current_step"] == 10
    assert result["project_count"] == 2
    assert result["budget_spent_usd"] == 2.5
    assert result["budget_limit_usd"] == 50.0
    assert "active_blocker" not in result


# ---------------------------------------------------------------------------
# test_summary_with_blocker
# ---------------------------------------------------------------------------


def test_summary_with_blocker(tmp_path: Path) -> None:
    state_path = tmp_path / "state.yaml"
    manifest_path = tmp_path / "manifest.yaml"

    _write_yaml(
        state_path,
        _make_state(active_blocker="scope_false_positive"),
    )
    _write_yaml(manifest_path, _make_manifest())

    result = load_dashboard_summary(state_path, manifest_path)

    assert result["found"] is True
    assert result["active_blocker"] == "scope_false_positive"


# ---------------------------------------------------------------------------
# test_summary_budget_tracking
# ---------------------------------------------------------------------------


def test_summary_budget_tracking(tmp_path: Path) -> None:
    state_path = tmp_path / "state.yaml"
    manifest_path = tmp_path / "manifest.yaml"

    _write_yaml(
        state_path,
        _make_state(current_step=4, budget_spent_usd=8.0),
    )
    _write_yaml(manifest_path, _make_manifest(budget_limit_usd=100.0))

    result = load_dashboard_summary(state_path, manifest_path)

    assert result["found"] is True
    # burn_rate = 8.0 / max(4, 1) = 2.0
    assert result["burn_rate_per_step"] == 2.0
    assert result["budget_limit_usd"] == 100.0
    assert result["budget_spent_usd"] == 8.0


# ---------------------------------------------------------------------------
# test_summary_file_not_found
# ---------------------------------------------------------------------------


def test_summary_file_not_found(tmp_path: Path) -> None:
    missing_state = tmp_path / "nonexistent_state.yaml"
    missing_manifest = tmp_path / "nonexistent_manifest.yaml"

    result = load_dashboard_summary(missing_state, missing_manifest)
    assert result == {"found": False}

    # Also test with only one file missing
    state_path = tmp_path / "state.yaml"
    _write_yaml(state_path, _make_state())
    result2 = load_dashboard_summary(state_path, missing_manifest)
    assert result2 == {"found": False}


# ---------------------------------------------------------------------------
# test_project_lifecycle_mixed
# ---------------------------------------------------------------------------


def test_project_lifecycle_mixed(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"

    projects = [
        {
            "project_id": "p1",
            "title": "Auth fix",
            "status": "completed",
            "retry_count": 0,
            "last_run_outcome": "deliverable_created",
            "estimated_cost_usd": 1.0,
        },
        {
            "project_id": "p2",
            "title": "Rate limiting",
            "status": "active",
            "retry_count": 0,
            "estimated_cost_usd": 0.5,
        },
        {
            "project_id": "p3",
            "title": "DB migration",
            "status": "failed",
            "retry_count": 2,
            "last_run_outcome": "crash",
            "estimated_cost_usd": 2.0,
        },
        {
            "project_id": "p4",
            "title": "Docs update",
            "status": "pending",
            "retry_count": 0,
            "estimated_cost_usd": 0.3,
        },
        {
            "project_id": "p5",
            "title": "Cleanup",
            "status": "completed",
            "retry_count": 1,
            "last_run_outcome": "deliverable_created",
            "estimated_cost_usd": 0.8,
        },
    ]
    _write_yaml(manifest_path, _make_manifest(projects=projects))

    result = load_project_lifecycle(manifest_path)

    assert result["found"] is True
    assert result["total_projects"] == 5
    assert len(result["by_status"]["completed"]) == 2
    assert len(result["by_status"]["active"]) == 1
    assert len(result["by_status"]["failed"]) == 1
    assert len(result["by_status"]["pending"]) == 1

    # Verify project detail shape
    completed = result["by_status"]["completed"][0]
    assert completed["project_id"] == "p1"
    assert completed["title"] == "Auth fix"
    assert completed["retry_count"] == 0


# ---------------------------------------------------------------------------
# test_blocker_history_by_kind
# ---------------------------------------------------------------------------


def test_blocker_history_by_kind(tmp_path: Path) -> None:
    state_path = tmp_path / "state.yaml"

    history = [
        {"kind": "scope_false_positive", "step": 2},
        {"kind": "scope_false_positive", "step": 5},
        {"kind": "worker_context_overflow", "step": 7},
        {"kind": "budget_exhaustion", "step": 9},
    ]
    _write_yaml(state_path, _make_state(blocker_history=history))

    result = load_blocker_history(state_path)

    assert result["found"] is True
    assert result["total_blockers"] == 4
    assert result["by_kind"]["scope_false_positive"] == 2
    assert result["by_kind"]["worker_context_overflow"] == 1
    assert result["by_kind"]["budget_exhaustion"] == 1


# ---------------------------------------------------------------------------
# test_blocker_deterministic_vs_escalation
# ---------------------------------------------------------------------------


def test_blocker_deterministic_vs_escalation(tmp_path: Path) -> None:
    state_path = tmp_path / "state.yaml"

    history = [
        # Deterministic kinds
        {"kind": "scope_false_positive"},
        {"kind": "worker_context_overflow"},
        {"kind": "receipt_emission_gap"},
        # Escalation kinds
        {"kind": "budget_exhaustion"},
        {"kind": "unknown"},
    ]
    _write_yaml(state_path, _make_state(blocker_history=history))

    result = load_blocker_history(state_path)

    assert result["found"] is True
    assert result["deterministic_count"] == 3
    assert result["escalation_count"] == 2
    assert result["total_blockers"] == 5
