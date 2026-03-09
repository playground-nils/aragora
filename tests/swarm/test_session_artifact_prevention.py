"""Tests for session artifact prevention in autonomous worker lanes.

Regression coverage for issue #879: autonomous workers that commit
.codex_session_meta.json must be detected and the artifact stripped from
deliverable output, not treated as valid user work.

Forensic evidence from the #873 Boss-loop failure showed a worker
committed .codex_session_meta.json alongside wrong-scope files.  The
supervisor accepted it as a valid changed path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aragora.nomic.dev_coordination import DevCoordinationStore
from aragora.swarm.supervisor import SwarmSupervisor
from aragora.swarm.worker_launcher import (
    SESSION_ARTIFACTS,
    LaunchConfig,
    WorkerLauncher,
    WorkerProcess,
)


UTC = __import__("datetime").timezone.utc


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(repo, "git", "init", "-b", "main")
    _run(repo, "git", "config", "user.email", "test@example.com")
    _run(repo, "git", "config", "user.name", "Test User")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _run(repo, "git", "add", "README.md")
    _run(repo, "git", "commit", "-m", "initial")
    _run(repo, "git", "remote", "add", "origin", str(repo))
    _run(repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


@pytest.fixture()
def store(repo: Path) -> DevCoordinationStore:
    return DevCoordinationStore(repo_root=repo)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, text=True, capture_output=True, check=True)


# ---------------------------------------------------------------------------
# SESSION_ARTIFACTS constant
# ---------------------------------------------------------------------------


class TestSessionArtifactsConstant:
    """Verify the canonical list of session artifacts."""

    def test_contains_codex_session_meta(self) -> None:
        assert ".codex_session_meta.json" in SESSION_ARTIFACTS

    def test_contains_codex_session_log(self) -> None:
        assert ".codex_session.log" in SESSION_ARTIFACTS

    def test_is_frozen(self) -> None:
        assert isinstance(SESSION_ARTIFACTS, frozenset)


# ---------------------------------------------------------------------------
# _strip_session_artifacts
# ---------------------------------------------------------------------------


class TestStripSessionArtifacts:
    """Test SwarmSupervisor._strip_session_artifacts."""

    def test_strips_session_meta(self) -> None:
        paths = [".codex_session_meta.json", "aragora/live/package.json"]
        result = SwarmSupervisor._strip_session_artifacts(paths)
        assert result == ["aragora/live/package.json"]

    def test_strips_session_log(self) -> None:
        paths = [".codex_session.log", "src/app.ts"]
        result = SwarmSupervisor._strip_session_artifacts(paths)
        assert result == ["src/app.ts"]

    def test_keeps_non_artifacts(self) -> None:
        paths = ["aragora/live/package.json", "README.md"]
        result = SwarmSupervisor._strip_session_artifacts(paths)
        assert result == paths

    def test_empty_list(self) -> None:
        assert SwarmSupervisor._strip_session_artifacts([]) == []

    def test_only_artifacts_returns_empty(self) -> None:
        """If session artifacts are the ONLY changes, result is empty."""
        paths = [".codex_session_meta.json", ".codex_session.log"]
        result = SwarmSupervisor._strip_session_artifacts(paths)
        assert result == []

    def test_nested_path_with_same_name_stripped(self) -> None:
        """Session artifacts under subdirs should also be stripped."""
        paths = ["subdir/.codex_session_meta.json", "aragora/live/app.ts"]
        result = SwarmSupervisor._strip_session_artifacts(paths)
        assert result == ["aragora/live/app.ts"]


# ---------------------------------------------------------------------------
# Worker prompt regression
# ---------------------------------------------------------------------------


class TestWorkerPromptNoGitAddAll:
    """Verify the worker prompt no longer instructs git add -A."""

    def test_prompt_does_not_instruct_git_add_all(self) -> None:
        """Prompt must not tell the worker to USE git add -A (warning against it is fine)."""
        work_order = {
            "title": "Test task",
            "description": "Do something",
            "file_scope": [],
            "metadata": {},
        }
        prompt = WorkerLauncher._build_prompt(work_order)
        # Must not contain an affirmative instruction to use git add -A
        assert "Stage all changed files with `git add -A`" not in prompt
        # Must contain a warning against using it
        assert "Do NOT use `git add -A`" in prompt

    def test_prompt_instructs_explicit_staging(self) -> None:
        work_order = {
            "title": "Test task",
            "description": "Do something",
            "file_scope": [],
            "metadata": {},
        }
        prompt = WorkerLauncher._build_prompt(work_order)
        assert "git add <file>" in prompt
        assert "session metadata files must not be committed" in prompt


# ---------------------------------------------------------------------------
# _apply_worker_result with session artifacts
# ---------------------------------------------------------------------------


class TestApplyWorkerResultSessionArtifacts:
    """Test that _apply_worker_result strips session artifacts."""

    def _make_supervisor(self, repo: Path, store: DevCoordinationStore) -> SwarmSupervisor:
        launcher = WorkerLauncher(config=LaunchConfig())
        return SwarmSupervisor(repo_root=repo, store=store, launcher=launcher)

    def test_session_meta_stripped_from_changed_paths(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Regression: .codex_session_meta.json must not appear as deliverable."""
        supervisor = self._make_supervisor(repo, store)
        item = {
            "work_order_id": "issue-879",
            "file_scope": [],
            "status": "dispatched",
            "lease_id": "",
            "target_agent": "codex",
        }
        result = WorkerProcess(
            work_order_id="issue-879",
            agent="codex",
            worktree_path=str(repo),
            branch="main",
            exit_code=0,
            changed_paths=[
                ".codex_session_meta.json",
                "aragora/live/package.json",
            ],
            commit_shas=["abc123"],
            head_sha="abc123",
        )
        supervisor._apply_worker_result(item, result)

        assert ".codex_session_meta.json" not in item["changed_paths"]
        assert "aragora/live/package.json" in item["changed_paths"]

    def test_only_session_meta_means_no_real_deliverable(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """If the only changed file is a session artifact, changed_paths is empty."""
        supervisor = self._make_supervisor(repo, store)
        item = {
            "work_order_id": "empty-work",
            "file_scope": [],
            "status": "dispatched",
            "lease_id": "",
            "target_agent": "codex",
        }
        result = WorkerProcess(
            work_order_id="empty-work",
            agent="codex",
            worktree_path=str(repo),
            branch="main",
            exit_code=0,
            changed_paths=[".codex_session_meta.json"],
            commit_shas=["def456"],
            head_sha="def456",
        )
        supervisor._apply_worker_result(item, result)

        assert item["changed_paths"] == []

    def test_regression_issue_873_forensic_paths(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Regression: exact paths from the #873 failure.

        The worker committed:
        - .codex_session_meta.json  (artifact — must be stripped)
        - README.md                 (wrong scope — must trigger scope violation)
        - docs/LANDING_PAGE.md      (wrong scope — must trigger scope violation)
        """
        supervisor = self._make_supervisor(repo, store)
        item = {
            "work_order_id": "issue-873-forensic",
            "file_scope": ["aragora/live"],
            "status": "dispatched",
            "lease_id": "",
            "target_agent": "codex",
        }
        result = WorkerProcess(
            work_order_id="issue-873-forensic",
            agent="codex",
            worktree_path=str(repo),
            branch="main",
            exit_code=0,
            changed_paths=[
                ".codex_session_meta.json",
                "README.md",
                "docs/LANDING_PAGE.md",
            ],
            commit_shas=["ghi789"],
            head_sha="ghi789",
        )
        supervisor._apply_worker_result(item, result)

        # Session artifact stripped
        assert ".codex_session_meta.json" not in item["changed_paths"]
        # Scope violation triggered for remaining wrong-scope files
        assert item["status"] == "scope_violation"
