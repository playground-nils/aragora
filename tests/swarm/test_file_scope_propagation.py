"""Regression tests for file-scope propagation from SwarmSpec to work orders.

Covers the bug where file_scope_hints from SwarmSpec were lost when the
TaskDecomposer returned subtasks with empty file_scope, causing scope
enforcement to be bypassed entirely (empty file_scope → no violations
detected → workers edit arbitrary files).

Root cause: _build_supervised_work_orders did not backfill file_scope
from spec.file_scope_hints onto decomposer-produced work orders.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aragora.nomic.dev_coordination import DevCoordinationStore
from aragora.nomic.task_decomposer import SubTask, TaskDecomposition
from aragora.swarm.spec import SwarmSpec
from aragora.swarm.supervisor import SwarmSupervisor


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True
    )
    (repo / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(repo)],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


@pytest.fixture()
def store(repo: Path) -> DevCoordinationStore:
    return DevCoordinationStore(repo_root=repo)


def _make_supervisor(
    repo: Path,
    store: DevCoordinationStore,
    subtasks: list[SubTask],
) -> SwarmSupervisor:
    lifecycle = MagicMock()
    decomposer = MagicMock()
    decomposer.analyze.return_value = TaskDecomposition(
        original_task="test",
        complexity_score=5,
        complexity_level="medium",
        should_decompose=True,
        subtasks=subtasks,
    )
    return SwarmSupervisor(
        repo_root=repo,
        store=store,
        lifecycle=lifecycle,
        decomposer=decomposer,
    )


class TestFileScopeBackfill:
    """Verify file_scope is backfilled from spec hints onto decomposer subtasks."""

    def test_empty_subtask_file_scope_backfilled_from_spec_hints(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """When decomposer returns subtasks with empty file_scope,
        the spec's file_scope_hints are propagated to the work orders."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Fix live page",
                description="Update eslintrc",
                file_scope=[],  # decomposer left this empty
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump eslintrc",
            file_scope_hints=["aragora/live", "@eslint/eslintrc"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert len(work_orders) == 1
        assert work_orders[0].file_scope == ["aragora/live", "@eslint/eslintrc"]

    def test_nonempty_subtask_file_scope_preserved(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """When decomposer correctly populates file_scope, spec hints
        do NOT override it."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Fix handler",
                description="Update handler",
                file_scope=["aragora/server/handlers/foo.py"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Fix handler",
            file_scope_hints=["aragora/server/"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/server/handlers/foo.py"]

    def test_no_spec_hints_no_backfill(self, repo: Path, store: DevCoordinationStore) -> None:
        """When spec has no file_scope_hints, empty subtask file_scope
        stays empty (no spurious backfill)."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="General task",
                description="Do something",
                file_scope=[],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(raw_goal="Do something", file_scope_hints=[])

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == []

    def test_multiple_subtasks_backfill_only_empty_ones(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Only subtasks with empty file_scope get backfilled; populated
        ones keep their specific scope."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Specific lane",
                description="Has scope",
                file_scope=["aragora/server/handlers/foo.py"],
            ),
            SubTask(
                id="wo-2",
                title="Empty lane",
                description="No scope from decomposer",
                file_scope=[],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Multi-lane task",
            file_scope_hints=["aragora/live", "aragora/server"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/server/handlers/foo.py"]
        assert work_orders[1].file_scope == ["aragora/live", "aragora/server"]

    def test_fallback_subtask_already_uses_spec_hints(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """When decomposer returns NO subtasks, the fallback path already
        populates file_scope from spec hints (pre-existing behavior)."""
        supervisor = _make_supervisor(repo, store, subtasks=[])
        spec = SwarmSpec(
            raw_goal="Single task",
            file_scope_hints=["aragora/cli/main.py"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert len(work_orders) == 1
        assert work_orders[0].file_scope == ["aragora/cli/main.py"]


class TestWrongScopeOverride:
    """Verify decomposer-produced scopes with zero overlap get overridden."""

    def test_wrong_decomposer_scope_overridden_by_spec_hints(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Decomposer returns unrelated scopes; they get replaced with spec hints."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Audit lane",
                description="Audit stuff",
                file_scope=["aragora/audit/codebase_auditor.py", "aragora/compliance/"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump eslintrc in aragora/live",
            file_scope_hints=["aragora/live"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/live"]

    def test_correct_narrower_decomposer_scope_preserved(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Decomposer correctly narrows within hint → preserved."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Fix handler",
                description="Fix",
                file_scope=["aragora/server/handlers/foo.py"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Fix handler",
            file_scope_hints=["aragora/server/"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/server/handlers/foo.py"]

    def test_multiple_subtasks_mixed_overlap(self, repo: Path, store: DevCoordinationStore) -> None:
        """Overlapping subtask keeps scope; non-overlapping gets overridden."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Correct lane",
                description="Within scope",
                file_scope=["aragora/live/package.json"],
            ),
            SubTask(
                id="wo-2",
                title="Wrong lane",
                description="Unrelated",
                file_scope=["aragora/audit/", "aragora/compliance/"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump eslintrc in aragora/live",
            file_scope_hints=["aragora/live"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/live/package.json"]
        assert work_orders[1].file_scope == ["aragora/live"]

    def test_issue_873_four_wrong_subtasks_all_overridden(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Forensic: decomposer returned 4 subtasks all with wrong scopes."""
        subtasks = [
            SubTask(id="s1", title="s1", description="s1", file_scope=[]),
            SubTask(
                id="s2",
                title="s2",
                description="s2",
                file_scope=["aragora/audit/", "aragora/compliance/"],
            ),
            SubTask(
                id="s3",
                title="s3",
                description="s3",
                file_scope=["aragora/compliance/"],
            ),
            SubTask(
                id="s4",
                title="s4",
                description="s4",
                file_scope=["sdk/", "docs/", "tests/sdk/"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump @eslint/eslintrc in /aragora/live",
            file_scope_hints=["aragora/live", "@eslint/eslintrc", "/aragora/live"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        for wo in work_orders:
            assert wo.file_scope == ["aragora/live", "@eslint/eslintrc", "/aragora/live"], (
                f"work order {wo.work_order_id} should have spec hints as scope"
            )

    def test_no_hints_with_wrong_scope_passes_through(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Without spec hints, decomposer scopes pass through unchanged."""
        subtasks = [
            SubTask(
                id="wo-1",
                title="Audit",
                description="Audit",
                file_scope=["aragora/audit/"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(raw_goal="Audit stuff", file_scope_hints=[])

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert work_orders[0].file_scope == ["aragora/audit/"]

    def test_overlap_bidirectional(self, repo: Path, store: DevCoordinationStore) -> None:
        """Overlap works in both directions: scope under hint AND hint under scope."""
        # Scope narrower than hint → overlap
        subtasks_narrow = [
            SubTask(
                id="wo-1",
                title="n",
                description="n",
                file_scope=["aragora/live/components/Nav.tsx"],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks_narrow)
        spec = SwarmSpec(raw_goal="fix", file_scope_hints=["aragora/live"])
        work_orders = supervisor._build_supervised_work_orders(spec)
        assert work_orders[0].file_scope == ["aragora/live/components/Nav.tsx"]

        # Scope wider than hint → overlap (decomposer widened, still relevant)
        subtasks_wide = [
            SubTask(
                id="wo-1",
                title="w",
                description="w",
                file_scope=["aragora"],
            ),
        ]
        supervisor2 = _make_supervisor(repo, store, subtasks_wide)
        spec2 = SwarmSpec(raw_goal="fix", file_scope_hints=["aragora/live"])
        work_orders2 = supervisor2._build_supervised_work_orders(spec2)
        assert work_orders2[0].file_scope == ["aragora"]


class TestScopeOverlapsHints:
    """Unit tests for the _scope_overlaps_hints static method."""

    def test_exact_match(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints(["aragora/live"], ["aragora/live"]) is True

    def test_scope_under_hint(self) -> None:
        assert (
            SwarmSupervisor._scope_overlaps_hints(["aragora/live/package.json"], ["aragora/live"])
            is True
        )

    def test_hint_under_scope(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints(["aragora"], ["aragora/live"]) is True

    def test_no_overlap(self) -> None:
        assert (
            SwarmSupervisor._scope_overlaps_hints(
                ["aragora/audit/", "aragora/compliance/"], ["aragora/live"]
            )
            is False
        )

    def test_empty_scope(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints([], ["aragora/live"]) is False

    def test_empty_hints(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints(["aragora/live"], []) is False

    def test_leading_dot_slash_stripped(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints(["./aragora/live"], ["aragora/live"]) is True

    def test_trailing_slash_stripped(self) -> None:
        assert SwarmSupervisor._scope_overlaps_hints(["aragora/live/"], ["aragora/live"]) is True

    def test_sibling_directory_no_false_positive(self) -> None:
        """aragora/livekit must NOT match aragora/live (boundary check)."""
        assert SwarmSupervisor._scope_overlaps_hints(["aragora/livekit"], ["aragora/live"]) is False

    def test_glob_hint_overlaps_concrete_scope(self) -> None:
        """Glob hint tests/sdk/** must overlap concrete scope tests/sdk/foo.py."""
        assert SwarmSupervisor._scope_overlaps_hints(["tests/sdk/foo.py"], ["tests/sdk/**"]) is True

    def test_concrete_hint_overlaps_glob_scope(self) -> None:
        """Concrete hint tests/sdk overlaps glob scope tests/sdk/**."""
        assert SwarmSupervisor._scope_overlaps_hints(["tests/sdk/**"], ["tests/sdk"]) is True

    def test_glob_no_overlap(self) -> None:
        """Glob patterns in different trees must not overlap."""
        assert (
            SwarmSupervisor._scope_overlaps_hints(["aragora/audit/**"], ["aragora/live/**"])
            is False
        )


class TestForensicIssue873Regression:
    """Reproduces the exact failure shape from the second Boss-loop test
    against issue #873: spec had file_scope_hints but work order dispatched
    with file_scope: [], causing scope enforcement to be bypassed."""

    def test_issue_873_shape_file_scope_not_lost(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """The exact forensic shape: spec.file_scope_hints = ["aragora/live",
        "@eslint/eslintrc", "/aragora/live"] but decomposer returns subtask
        with file_scope=[]. Work order MUST carry the spec hints."""
        subtasks = [
            SubTask(
                id="work-eslintrc",
                title="Bump @eslint/eslintrc",
                description="Update eslintrc dependency in aragora/live",
                file_scope=[],  # decomposer failed to populate
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump @eslint/eslintrc from 3.2.0 to 3.3.0 in /aragora/live",
            file_scope_hints=["aragora/live", "@eslint/eslintrc", "/aragora/live"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)

        assert len(work_orders) == 1
        wo = work_orders[0]
        assert wo.file_scope, "file_scope must not be empty when spec has hints"
        assert "aragora/live" in wo.file_scope

    def test_dispatched_work_order_dict_carries_file_scope(
        self, repo: Path, store: DevCoordinationStore
    ) -> None:
        """Verify the to_dict() representation (what gets stored and
        dispatched) also carries file_scope after backfill."""
        subtasks = [
            SubTask(
                id="work-bump",
                title="Bump dep",
                description="bump",
                file_scope=[],
            ),
        ]
        supervisor = _make_supervisor(repo, store, subtasks)
        spec = SwarmSpec(
            raw_goal="Bump dep",
            file_scope_hints=["aragora/live"],
        )

        work_orders = supervisor._build_supervised_work_orders(spec)
        wo_dict = work_orders[0].to_dict()

        assert wo_dict["file_scope"] == ["aragora/live"]
