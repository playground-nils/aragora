from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aragora.server.handlers.agent_bridge import AgentBridgeHandler
from aragora.swarm.agent_bridge import AgentBridgeBroker
from aragora.swarm.agent_bridge import BridgeSession
from aragora.swarm.agent_bridge import TurnRecord


def _parse(result: object) -> dict:
    return json.loads(result.body)  # type: ignore[attr-defined]


@pytest.fixture
def bridge_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("ARAGORA_AGENT_BRIDGE_REPO", str(tmp_path))
    return tmp_path


@pytest.fixture
def handler(bridge_repo: Path) -> AgentBridgeHandler:
    broker = AgentBridgeBroker(bridge_repo)
    run = broker.start_run(
        task="Review the fix",
        sessions={
            "codex-a": BridgeSession(
                role="implementer",
                harness="codex",
                model="gpt-5.4",
                session_id="thread-1",
                worktree_agent_slug="codex",
                worktree_path=str(bridge_repo / ".worktrees" / "agent-bridge" / "codex-a"),
                branch="codex/bridge-a",
                session_status="active",
                started_at="2026-04-21T18:00:00Z",
                last_turn_index=2,
                last_completed_at="2026-04-21T18:04:00Z",
            ),
            "claude-b": BridgeSession(
                role="reviewer",
                harness="claude",
                model="claude-opus-4-7",
                session_id=None,
                worktree_agent_slug="codex",
                worktree_path=None,
                branch=None,
                session_status="not_started",
                started_at=None,
                last_turn_index=0,
                last_completed_at=None,
            ),
        },
        run_id="run-123",
        next_actor="claude-b",
        worktree_path=str(bridge_repo),
        worktree_agent_slug="codex",
    )
    run.status = "awaiting_human"
    run.last_turn_index = 2
    run.updated_at = "2026-04-21T18:05:00Z"
    run.next_actor = "human"
    broker.store.save_run(run)
    broker.store.append_event(
        run.run_id,
        TurnRecord(
            event_id="run-123:turn:002:footer_ok:0",
            run_id=run.run_id,
            turn_index=2,
            event_type="footer_ok",
            role="claude-b",
            harness="claude",
            session_id="thread-2",
            ts="2026-04-21T18:03:00Z",
            parse_status="ok",
            payload={
                "footer": {
                    "summary": "Implemented bounded slice",
                    "next_actor": "claude-b",
                    "needs_human": False,
                    "done": False,
                    "artifacts": ["turns/0002-claude-b.md"],
                    "tests_run": ["pytest tests/swarm/test_agent_bridge.py -q"],
                },
                "transcript_path": ".aragora/agent_bridge/runs/run-123/turns/002-claude-b.md",
            },
        ),
    )
    return AgentBridgeHandler(ctx={})


def test_can_handle_bridge_routes(handler: AgentBridgeHandler) -> None:
    assert handler.can_handle("/api/v1/agent-bridge/runs")
    assert handler.can_handle("/api/agent-bridge/runs/run-123")
    assert not handler.can_handle("/api/v1/review-queue/prs")


def test_list_runs_returns_session_summary(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs", {"limit": "10"}, MagicMock())

    assert result is not None
    assert result.status_code == 200
    data = _parse(result)
    assert data["total"] == 1
    assert data["runs"][0]["run_id"] == "run-123"
    assert data["runs"][0]["session_count"] == 2
    assert data["runs"][0]["worktree_agent_slug"] == "codex"
    assert {item["name"] for item in data["runs"][0]["agents"]} == {"codex-a", "claude-b"}


def test_get_run_returns_sessions(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/run-123", {}, MagicMock())

    assert result is not None
    assert result.status_code == 200
    data = _parse(result)
    assert data["run"]["run_id"] == "run-123"
    assert data["run"]["status"] == "awaiting_human"
    assert len(data["sessions"]) == 2


def test_get_events_returns_event_log(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/run-123/events", {"limit": "5"}, MagicMock())

    assert result is not None
    assert result.status_code == 200
    data = _parse(result)
    assert data["count"] == 2
    assert [event["type"] for event in data["events"]] == ["run_started", "footer_ok"]
    assert data["events"][1]["footer"]["summary"] == "Implemented bounded slice"


def test_unknown_run_returns_404(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/missing", {}, MagicMock())

    assert result is not None
    assert result.status_code == 404
