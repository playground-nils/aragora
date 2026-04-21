from __future__ import annotations

from pathlib import Path

from aragora.swarm.agent_bridge.broker import AgentBridgeBroker
from aragora.swarm.agent_bridge.footer import FOOTER_PREFIX
from aragora.swarm.agent_bridge.footer import extract_footer
from aragora.swarm.agent_bridge.store import BridgeStore
from aragora.swarm.agent_bridge.transport import ClaudeTransport
from aragora.swarm.agent_bridge.transport import CodexTransport
from aragora.swarm.agent_bridge.transport import DroidTransport
from aragora.swarm.agent_bridge.types import BridgeRun
from aragora.swarm.agent_bridge.types import BridgeSession
from aragora.swarm.agent_bridge.types import BridgeTurnResult
from aragora.swarm.agent_bridge.types import HarnessKind


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent_bridge"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_footer_returns_body_and_footer() -> None:
    text = (
        "Implemented the bounded fix.\n"
        f"{FOOTER_PREFIX} "
        '{"summary":"Patched config loader","next_actor":"reviewer","needs_human":false,'
        '"done":false,"artifacts":["tests/pdb/test_panel_config.py"],'
        '"tests_run":["pytest tests/pdb/test_panel_config.py -q"]}'
    )

    footer, body = extract_footer(text)

    assert footer is not None
    assert footer.summary == "Patched config loader"
    assert footer.next_actor == "reviewer"
    assert footer.tests_run == ["pytest tests/pdb/test_panel_config.py -q"]
    assert body == "Implemented the bounded fix."


def test_bridge_store_round_trip(tmp_path: Path) -> None:
    store = BridgeStore(tmp_path)
    run = BridgeRun(run_id="run-123", task="Inspect cross-harness recall", repo_root=str(tmp_path))
    session = BridgeSession(name="codex-a", harness=HarnessKind.CODEX, role="implementer")

    store.save_run(run)
    store.save_sessions(run.run_id, [session])
    store.append_event(run.run_id, "run_created", actor="codex-a")

    loaded_run = store.load_run(run.run_id)
    loaded_sessions = store.load_sessions(run.run_id)
    loaded_events = store.load_events(run.run_id)

    assert loaded_run.to_dict() == run.to_dict()
    assert [item.to_dict() for item in loaded_sessions] == [session.to_dict()]
    assert loaded_events[0]["type"] == "run_created"


def test_codex_parse_fixture_captures_thread_id() -> None:
    transport = CodexTransport()

    result = transport._parse(
        _fixture("codex_first_turn.jsonl"),
        "",
        "Review completed.",
    )

    assert result.session_id == "019db14c-6f2d-75f6-856d-615d3cdcd7c9"
    assert result.response_text == "Review completed."
    assert result.metadata["usage"]["output_tokens"] == 64


def test_codex_resume_parse_uses_existing_session_id_hint() -> None:
    transport = CodexTransport()

    result = transport._parse(
        _fixture("codex_resume_turn.jsonl"),
        "",
        "Follow-up response.",
        session_id_hint="thread-existing",
    )

    assert result.session_id == "thread-existing"
    assert result.metadata["stop_reason"] == "completed"


def test_droid_parse_fixture_captures_session_id() -> None:
    transport = DroidTransport()

    result = transport._parse(_fixture("droid_first_turn.json"), "")

    assert result.session_id == "16329fce-3484-47a4-ad98-6676fdfb7477"
    assert result.response_text == "OK"
    assert result.metadata["num_turns"] == 1


def test_claude_build_cmd_uses_resume_and_explicit_session_id() -> None:
    transport = ClaudeTransport()
    session = BridgeSession(name="claude-review", harness=HarnessKind.CLAUDE, session_id="sess-1")

    start_cmd = transport._build_cmd(
        BridgeSession(name="claude-review", harness=HarnessKind.CLAUDE),
        "hello",
        resume=False,
    )
    resume_cmd = transport._build_cmd(session, "again", resume=True)

    assert "--session-id" in start_cmd
    assert "--resume" in resume_cmd
    assert resume_cmd[resume_cmd.index("--resume") + 1] == "sess-1"


def test_broker_dispatch_turn_persists_run_and_events(monkeypatch, tmp_path: Path) -> None:
    broker = AgentBridgeBroker(tmp_path)
    sessions = [BridgeSession(name="codex-a", harness=HarnessKind.CODEX, role="implementer")]
    run = broker.create_run(task="Implement a bounded fix", sessions=sessions, run_id="run-001")

    def fake_ensure_worktree(*, session: BridgeSession, base_branch: str) -> None:
        session.worktree_path = str(tmp_path)
        session.branch = f"codex/{base_branch}/codex-a"

    class FakeTransport:
        def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
            assert "AGENT_BRIDGE_FOOTER:" in prompt
            return BridgeTurnResult(
                session_id="thread-1",
                response_text=(
                    "Implemented the change.\n"
                    f"{FOOTER_PREFIX} "
                    '{"summary":"Implemented the change","next_actor":"reviewer",'
                    '"needs_human":false,"done":false,"artifacts":["artifact.json"],'
                    '"tests_run":["pytest tests/swarm/test_agent_bridge.py -q"]}'
                ),
                raw_stdout="",
                raw_stderr="",
            )

    monkeypatch.setattr(broker, "_ensure_worktree", fake_ensure_worktree)
    monkeypatch.setattr(
        "aragora.swarm.agent_bridge.broker.transport_for", lambda session: FakeTransport()
    )

    result = broker.dispatch_turn(
        run_id=run.run_id, actor="codex-a", prompt="Make the bounded edit."
    )
    reloaded = AgentBridgeBroker(tmp_path)

    assert result.footer is not None
    assert result.footer.summary == "Implemented the change"
    loaded_run = reloaded.load_run(run.run_id)
    loaded_sessions = reloaded.load_sessions(run.run_id)
    loaded_events = reloaded.load_events(run.run_id)
    turn_artifact = (
        tmp_path / ".aragora" / "agent_bridge" / "runs" / run.run_id / "turns" / "0001-codex-a.json"
    )

    assert loaded_run.active_actor == "reviewer"
    assert loaded_sessions[0].session_id == "thread-1"
    assert turn_artifact.exists()
    assert any(event["type"] == "turn_completed" for event in loaded_events)


def test_broker_requests_footer_repair_once(monkeypatch, tmp_path: Path) -> None:
    broker = AgentBridgeBroker(tmp_path)
    sessions = [BridgeSession(name="droid-review", harness=HarnessKind.DROID, role="reviewer")]
    run = broker.create_run(task="Review the patch", sessions=sessions, run_id="run-002")

    def fake_ensure_worktree(*, session: BridgeSession, base_branch: str) -> None:
        session.worktree_path = str(tmp_path)
        session.branch = f"droid/{base_branch}/review"

    class FakeTransport:
        def __init__(self) -> None:
            self.calls = 0

        def start_session(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
            self.calls += 1
            return BridgeTurnResult(
                session_id="droid-session",
                response_text="Here is the review without the footer.",
                raw_stdout="",
                raw_stderr="",
            )

        def resume_turn(self, session: BridgeSession, prompt: str) -> BridgeTurnResult:
            self.calls += 1
            assert "Return exactly one line containing only a corrected footer." in prompt
            return BridgeTurnResult(
                session_id="droid-session",
                response_text=(
                    f"{FOOTER_PREFIX} "
                    '{"summary":"Footer repaired","next_actor":null,"needs_human":true,'
                    '"done":false,"artifacts":[],"tests_run":[]}'
                ),
                raw_stdout="",
                raw_stderr="",
            )

    transport = FakeTransport()
    monkeypatch.setattr(broker, "_ensure_worktree", fake_ensure_worktree)
    monkeypatch.setattr(
        "aragora.swarm.agent_bridge.broker.transport_for", lambda session: transport
    )

    result = broker.dispatch_turn(run_id=run.run_id, actor="droid-review", prompt="Review it.")
    events = broker.load_events(run.run_id)

    assert result.footer is not None
    assert result.footer.summary == "Footer repaired"
    assert transport.calls == 2
    assert any(event["type"] == "footer_repair_requested" for event in events)
    assert any(event["type"] == "footer_repair_completed" for event in events)
