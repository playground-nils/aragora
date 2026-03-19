"""Test CLI integrator view rendering."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestSwarmIntegratorCLI:
    def test_integrator_json_output(self, capsys):
        mock_view = {
            "summary": {"total_lanes": 1},
            "lanes": [
                {
                    "lane_id": "l1",
                    "branch": "fix/bug",
                    "merge_readiness": "ready",
                }
            ],
            "next_actions": [],
            "alerts": [],
        }
        with patch("aragora.swarm.reporter.build_integrator_view", return_value=mock_view):
            from aragora.swarm.reporter import build_integrator_view

            view = build_integrator_view(runs=[], worktrees=[], claims=[], merge_queue=[])
            print(json.dumps(view, indent=2))
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["summary"]["total_lanes"] == 1

    def test_integrator_table_renders(self, capsys):
        mock_view = {
            "summary": {"total_lanes": 2, "ready_lanes": 1, "blocked_lanes": 1},
            "lanes": [
                {
                    "lane_id": "l1",
                    "title": "Fix auth",
                    "branch": "fix/auth",
                    "merge_readiness": "ready",
                    "status": "completed",
                    "blockers": [],
                    "next_action": "merge",
                },
                {
                    "lane_id": "l2",
                    "title": "Add tests",
                    "branch": "test/add",
                    "merge_readiness": "blocked",
                    "status": "in_progress",
                    "blockers": ["CI failing"],
                    "next_action": "fix CI",
                },
            ],
            "next_actions": ["Merge fix/auth"],
            "alerts": [],
        }
        from aragora.cli.commands.swarm import _render_integrator_table

        _render_integrator_table(mock_view)
        captured = capsys.readouterr()
        assert "Fix auth" in captured.out
        assert "ready" in captured.out
        assert "Add tests" in captured.out
        assert "blocked" in captured.out
        assert "CI failing" in captured.out
