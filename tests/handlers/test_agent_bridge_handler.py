from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aragora.server.handlers.agent_bridge import AgentBridgeHandler
from aragora.swarm.agent_bridge import AgentBridgeBroker
from aragora.swarm.agent_bridge import BridgeSession
from aragora.swarm.agent_bridge import HarnessKind


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
    run = broker.create_run(
        task="Review the fix",
        sessions=[
            BridgeSession(name="codex-a", harness=HarnessKind.CODEX, role="implementer"),
            BridgeSession(name="claude-b", harness=HarnessKind.CLAUDE, role="reviewer"),
        ],
        run_id="run-123",
    )
    broker.store.append_event(
        run.run_id,
        "turn_completed",
        actor="codex-a",
        footer={
            "summary": "Implemented bounded slice",
            "next_actor": "claude-b",
            "needs_human": False,
            "done": False,
            "artifacts": ["turns/0001-codex-a.json"],
            "tests_run": ["pytest tests/swarm/test_agent_bridge.py -q"],
        },
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
    assert {item["name"] for item in data["runs"][0]["agents"]} == {"codex-a", "claude-b"}


def test_get_run_returns_sessions(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/run-123", {}, MagicMock())

    assert result is not None
    assert result.status_code == 200
    data = _parse(result)
    assert data["run"]["run_id"] == "run-123"
    assert len(data["sessions"]) == 2


def test_get_events_returns_event_log(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/run-123/events", {"limit": "5"}, MagicMock())

    assert result is not None
    assert result.status_code == 200
    data = _parse(result)
    assert data["count"] == 2
    assert [event["type"] for event in data["events"]] == ["run_created", "turn_completed"]


def test_unknown_run_returns_404(handler: AgentBridgeHandler) -> None:
    result = handler.handle("/api/v1/agent-bridge/runs/missing", {}, MagicMock())

    assert result is not None
    assert result.status_code == 404
