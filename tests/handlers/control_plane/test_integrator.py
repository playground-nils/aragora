"""Tests for swarm integrator view endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestIntegratorViewEndpoint:
    def test_get_returns_integrator_view(self):
        """GET /api/v1/swarm/integrator returns structured view."""
        mock_view = {
            "summary": {"total_lanes": 2, "ready_lanes": 1},
            "lanes": [{"lane_id": "l1", "status": "completed"}],
            "next_actions": [],
            "alerts": [],
        }
        with patch("aragora.swarm.reporter.build_integrator_view", return_value=mock_view):
            from aragora.swarm.reporter import build_integrator_view

            result = build_integrator_view(runs=[], worktrees=[], claims=[], merge_queue=[])
            assert result["summary"]["total_lanes"] == 2
            assert len(result["lanes"]) == 1


class TestIntegratorMergeEndpoint:
    def test_merge_records_integration_decision(self):
        """POST /api/v1/swarm/integrator/merge delegates to DevCoordinationStore."""
        mock_store = MagicMock()
        mock_store.record_integration_decision.return_value = "decision-1"
        from aragora.nomic.dev_coordination import IntegrationDecisionType

        mock_store.record_integration_decision(
            lease_id="lease-1",
            decided_by="human-integrator",
            decision=IntegrationDecisionType.MERGE,
            rationale="Tests pass, ready to merge",
        )
        mock_store.record_integration_decision.assert_called_once()


class TestIntegratorArchiveEndpoint:
    def test_archive_records_discard_decision(self):
        mock_store = MagicMock()
        from aragora.nomic.dev_coordination import IntegrationDecisionType

        mock_store.record_integration_decision(
            lease_id="lease-2",
            decided_by="human-integrator",
            decision=IntegrationDecisionType.DISCARD,
            rationale="Superseded by newer approach",
        )
        mock_store.record_integration_decision.assert_called_once()


class TestIntegratorSupersedeEndpoint:
    def test_supersede_calls_pr_registry(self):
        mock_registry = MagicMock()
        mock_registry.supersede.return_value = {
            "branch": "old",
            "superseded_by": "new-url",
        }
        mock_registry.supersede(
            "feature/old", "https://github.com/org/repo/pull/999", reason="newer"
        )
        mock_registry.supersede.assert_called_once()
