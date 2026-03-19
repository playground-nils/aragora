"""Tests for PullRequestRegistry — canonical PR tracking across swarm workers."""

from __future__ import annotations

from pathlib import Path

import pytest

from aragora.swarm.pr_registry import PREntry, PullRequestRegistry


class TestPREntry:
    """Unit tests for the PREntry dataclass."""

    def test_default_created_at(self):
        entry = PREntry(branch="fix/a", pr_url="https://example.com/pr/1", creator="w1")
        assert entry.created_at != ""
        assert entry.status == "active"
        assert entry.superseded == []
        assert entry.gate_snapshot is None
        assert entry.metadata == {}

    def test_explicit_created_at(self):
        entry = PREntry(
            branch="fix/a",
            pr_url="https://example.com/pr/1",
            creator="w1",
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert entry.created_at == "2026-01-01T00:00:00+00:00"


class TestPullRequestRegistry:
    """Unit tests for the YAML-backed PullRequestRegistry."""

    def test_register_pr(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/scope", "https://github.com/org/repo/pull/42", creator="worker-1")
        entry = registry.get("fix/scope")
        assert entry is not None
        assert entry["pr_url"] == "https://github.com/org/repo/pull/42"
        assert entry["creator"] == "worker-1"
        assert entry["status"] == "active"

    def test_supersede_pr(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/scope", "https://github.com/org/repo/pull/42", creator="worker-1")
        registry.supersede(
            "fix/scope",
            "https://github.com/org/repo/pull/43",
            reason="newer implementation",
        )
        entry = registry.get("fix/scope")
        assert entry is not None
        assert entry["pr_url"] == "https://github.com/org/repo/pull/43"
        assert len(entry["superseded"]) == 1
        assert entry["superseded"][0]["pr_url"] == "https://github.com/org/repo/pull/42"
        assert entry["superseded"][0]["reason"] == "newer implementation"

    def test_auto_supersede_on_register_same_branch(self, tmp_path: Path):
        """Registering a PR on a branch that already has an active PR should supersede it."""
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/scope", "https://github.com/org/repo/pull/42", creator="worker-1")
        registry.register("fix/scope", "https://github.com/org/repo/pull/99", creator="worker-2")
        entry = registry.get("fix/scope")
        assert entry is not None
        assert entry["pr_url"] == "https://github.com/org/repo/pull/99"
        assert len(entry["superseded"]) == 1
        assert entry["superseded"][0]["pr_url"] == "https://github.com/org/repo/pull/42"

    def test_close_pr(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/a", "url-1", creator="w1")
        result = registry.close("fix/a", outcome="merged")
        assert result is not None
        entry = registry.get("fix/a")
        assert entry is not None
        assert entry["status"] == "merged"

    def test_close_nonexistent_branch(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        result = registry.close("nonexistent", outcome="closed")
        assert result is None

    def test_list_active_filters_out_closed(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/a", "url-1", creator="w1")
        registry.register("fix/b", "url-2", creator="w2")
        registry.close("fix/a", outcome="merged")
        active = registry.list_active()
        assert len(active) == 1
        assert active[0]["branch"] == "fix/b"

    def test_list_all_includes_closed(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/a", "url-1", creator="w1")
        registry.register("fix/b", "url-2", creator="w2")
        registry.close("fix/a", outcome="merged")
        all_entries = registry.list_all()
        assert len(all_entries) == 2

    def test_persistence_round_trip(self, tmp_path: Path):
        """Register in one instance, load in another, data survives."""
        registry1 = PullRequestRegistry(state_dir=tmp_path)
        registry1.register("fix/scope", "https://example.com/pr/42", creator="worker-1")
        registry1.register("fix/other", "https://example.com/pr/43", creator="worker-2")

        # New instance loads from same directory
        registry2 = PullRequestRegistry(state_dir=tmp_path)
        entry = registry2.get("fix/scope")
        assert entry is not None
        assert entry["pr_url"] == "https://example.com/pr/42"
        assert entry["creator"] == "worker-1"

        other = registry2.get("fix/other")
        assert other is not None
        assert other["pr_url"] == "https://example.com/pr/43"

    def test_register_with_metadata(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register(
            "fix/scope",
            "https://example.com/pr/42",
            creator="worker-1",
            metadata={"issue": "#841", "priority": "high"},
        )
        entry = registry.get("fix/scope")
        assert entry is not None
        assert entry["metadata"]["issue"] == "#841"
        assert entry["metadata"]["priority"] == "high"

    def test_register_with_gate_snapshot(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        snapshot = {"checks_passed": True, "reviews_approved": 1}
        registry.register(
            "fix/scope",
            "https://example.com/pr/42",
            creator="worker-1",
            gate_snapshot=snapshot,
        )
        entry = registry.get("fix/scope")
        assert entry is not None
        assert entry["gate_snapshot"] == snapshot

    def test_supersede_nonexistent_branch(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        result = registry.supersede("nonexistent", "https://example.com/pr/1")
        assert result is None

    def test_get_nonexistent_branch(self, tmp_path: Path):
        registry = PullRequestRegistry(state_dir=tmp_path)
        assert registry.get("nonexistent") is None

    def test_register_on_closed_branch_creates_new_entry(self, tmp_path: Path):
        """After closing a PR, registering a new one for the same branch replaces it."""
        registry = PullRequestRegistry(state_dir=tmp_path)
        registry.register("fix/a", "url-1", creator="w1")
        registry.close("fix/a", outcome="closed")
        # Now register a new PR for the same branch — should NOT supersede since old is closed
        registry.register("fix/a", "url-2", creator="w2")
        entry = registry.get("fix/a")
        assert entry is not None
        assert entry["pr_url"] == "url-2"
        assert entry["status"] == "active"
        assert entry["superseded"] == []  # fresh entry, no supersede history

    def test_corrupted_yaml_recovers(self, tmp_path: Path):
        """If the YAML file is corrupted, the registry starts empty."""
        yaml_file = tmp_path / "pr_registry.yaml"
        yaml_file.write_text(":::not valid yaml{{{}}")
        registry = PullRequestRegistry(state_dir=tmp_path)
        assert registry.list_all() == []


class TestSwarmSupervisorPRRegistryIntegration:
    """Verify the PR registry integration pattern with SwarmSupervisor."""

    def test_get_pr_registry_returns_registry(self, tmp_path: Path):
        """SwarmSupervisor._get_pr_registry() should return a PullRequestRegistry."""
        from unittest.mock import MagicMock

        from aragora.swarm.supervisor import SwarmSupervisor

        sup = SwarmSupervisor.__new__(SwarmSupervisor)
        sup.repo_root = tmp_path
        sup.store = MagicMock()
        sup.lifecycle = MagicMock()
        sup.bridge = MagicMock()
        sup.decomposer = MagicMock()
        sup.approval_policy = MagicMock()
        sup.launcher = MagicMock()
        sup._pr_registry = None

        registry = sup._get_pr_registry()
        assert isinstance(registry, PullRequestRegistry)

        # Should return the same instance on second call (lazy init)
        assert sup._get_pr_registry() is registry

    def test_get_pr_registry_uses_aragora_dir(self, tmp_path: Path):
        """PR registry should be stored under repo_root/.aragora/."""
        from unittest.mock import MagicMock

        from aragora.swarm.supervisor import SwarmSupervisor

        sup = SwarmSupervisor.__new__(SwarmSupervisor)
        sup.repo_root = tmp_path
        sup.store = MagicMock()
        sup.lifecycle = MagicMock()
        sup.bridge = MagicMock()
        sup.decomposer = MagicMock()
        sup.approval_policy = MagicMock()
        sup.launcher = MagicMock()
        sup._pr_registry = None

        registry = sup._get_pr_registry()
        registry.register("fix/test", "https://example.com/pr/1", creator="test")
        assert (tmp_path / ".aragora" / "pr_registry.yaml").exists()


class TestRalphSupervisorPRRegistryIntegration:
    """Verify the PR registry integration pattern with RalphSupervisor."""

    def test_get_pr_registry_returns_registry(self, tmp_path: Path):
        """RalphSupervisor._get_pr_registry() should return a PullRequestRegistry."""
        from aragora.ralph.supervisor import RalphSupervisor

        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text("campaign_id: test\nprojects: []\n")
        state_path = tmp_path / "state.yaml"

        sup = RalphSupervisor(
            state_path=state_path,
            repo_root=tmp_path,
        )

        registry = sup._get_pr_registry()
        assert isinstance(registry, PullRequestRegistry)

        # Same instance on second call
        assert sup._get_pr_registry() is registry
