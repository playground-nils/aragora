"""Tests for the lightweight session coordination protocol."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aragora.swarm.session_coordinator import (
    claim_file,
    claim_pr,
    get_my_assignment,
    read_directives,
    report_finding,
    set_assignment,
    write_directives,
)


@pytest.fixture()
def coord_dir(tmp_path: Path) -> Path:
    """Create a temporary repo root with coordination dir."""
    (tmp_path / ".aragora" / "coordination").mkdir(parents=True)
    return tmp_path


class TestReadWriteDirectives:
    def test_read_empty_returns_defaults(self, coord_dir: Path) -> None:
        d = read_directives(coord_dir)
        assert "issued_at" in d
        assert "sessions" in d
        assert d["sessions"] == {}
        assert d["shared_findings"] == []
        assert d["claimed_prs"] == {}
        assert d["claimed_files"] == {}

    def test_roundtrip(self, coord_dir: Path) -> None:
        d = read_directives(coord_dir)
        d["sessions"]["test"] = {"role": "tester", "task": "run tests"}
        write_directives(d, coord_dir)
        d2 = read_directives(coord_dir)
        assert d2["sessions"]["test"]["task"] == "run tests"

    def test_read_corrupted_returns_defaults(self, coord_dir: Path) -> None:
        path = coord_dir / ".aragora" / "coordination" / "directives.json"
        path.write_text("NOT JSON{{{")
        d = read_directives(coord_dir)
        assert d["sessions"] == {}


class TestClaimPR:
    def test_claim_succeeds(self, coord_dir: Path) -> None:
        assert claim_pr(42, "claude-a", coord_dir) is True
        d = read_directives(coord_dir)
        assert d["claimed_prs"]["42"] == "claude-a"

    def test_claim_same_session_idempotent(self, coord_dir: Path) -> None:
        assert claim_pr(42, "claude-a", coord_dir) is True
        assert claim_pr(42, "claude-a", coord_dir) is True

    def test_claim_conflict(self, coord_dir: Path) -> None:
        assert claim_pr(42, "claude-a", coord_dir) is True
        assert claim_pr(42, "codex-b", coord_dir) is False
        d = read_directives(coord_dir)
        assert d["claimed_prs"]["42"] == "claude-a"


class TestClaimFile:
    def test_claim_file_succeeds(self, coord_dir: Path) -> None:
        assert claim_file("foo.py", "claude-a", coord_dir) is True
        d = read_directives(coord_dir)
        assert d["claimed_files"]["foo.py"] == "claude-a"

    def test_claim_file_conflict(self, coord_dir: Path) -> None:
        assert claim_file("foo.py", "claude-a", coord_dir) is True
        assert claim_file("foo.py", "codex-b", coord_dir) is False


class TestReportFinding:
    def test_append_finding(self, coord_dir: Path) -> None:
        report_finding("lint fails", "claude-a", coord_dir)
        report_finding("test flaky", "codex-b", coord_dir)
        d = read_directives(coord_dir)
        assert len(d["shared_findings"]) == 2
        assert d["shared_findings"][0]["finding"] == "lint fails"
        assert d["shared_findings"][0]["reported_by"] == "claude-a"
        assert d["shared_findings"][1]["finding"] == "test flaky"


class TestAssignments:
    def test_set_and_get(self, coord_dir: Path) -> None:
        set_assignment(
            "claude-a",
            "Fix tests",
            scope=["tests/"],
            constraints=["no refactoring"],
            role="fixer",
            repo_root=coord_dir,
        )
        assignment = get_my_assignment("claude-a", coord_dir)
        assert assignment is not None
        assert assignment["task"] == "Fix tests"
        assert assignment["role"] == "fixer"
        assert assignment["scope"] == ["tests/"]
        assert assignment["constraints"] == ["no refactoring"]
        assert assignment["status"] == "active"

    def test_get_unassigned_returns_none(self, coord_dir: Path) -> None:
        assert get_my_assignment("nobody", coord_dir) is None

    def test_multiple_sessions(self, coord_dir: Path) -> None:
        set_assignment("claude-a", "task A", repo_root=coord_dir)
        set_assignment("codex-b", "task B", repo_root=coord_dir)
        assert get_my_assignment("claude-a", coord_dir)["task"] == "task A"
        assert get_my_assignment("codex-b", coord_dir)["task"] == "task B"

    def test_issued_by_recorded(self, coord_dir: Path) -> None:
        set_assignment("claude-a", "task", issued_by="boss", repo_root=coord_dir)
        d = read_directives(coord_dir)
        assert d["issued_by"] == "boss"
