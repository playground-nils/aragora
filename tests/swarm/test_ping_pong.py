"""Tests for ping-pong orchestration pattern."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from aragora.swarm.ping_pong import (
    PingPongLoop,
    PingPongResult,
    PingPongRound,
    build_handoff_prompt,
)


def test_build_handoff_prompt_includes_context():
    prompt = build_handoff_prompt(
        goal="Fix failing tests",
        previous_transcript="Fixed 3 tests in debate/",
        previous_agent="claude",
        next_agent="codex",
        round_number=1,
        files_changed=["aragora/debate/orchestrator.py"],
        remaining_issues=["test_consensus still fails"],
    )
    assert "Fix failing tests" in prompt
    assert "claude" in prompt
    assert "codex" in prompt
    assert "Fixed 3 tests" in prompt
    assert "orchestrator.py" in prompt
    assert "test_consensus still fails" in prompt
    assert "round 2" in prompt.lower()


def test_build_handoff_prompt_truncates_long_transcript():
    long_transcript = "x" * 5000
    prompt = build_handoff_prompt(
        goal="goal",
        previous_transcript=long_transcript,
        previous_agent="a",
        next_agent="b",
        round_number=1,
    )
    assert len(prompt) < 5000


def test_ping_pong_round_auto_timestamp():
    r = PingPongRound(round_number=1, agent="claude", input_prompt="test")
    assert r.timestamp
    assert "T" in r.timestamp


def test_ping_pong_result_properties():
    result = PingPongResult(
        goal="test",
        rounds=[
            PingPongRound(round_number=1, agent="claude", input_prompt="p1"),
            PingPongRound(round_number=2, agent="codex", input_prompt="p2"),
        ],
        completed=True,
    )
    assert result.total_rounds == 2
    assert result.agents_used == ["claude", "codex"]


@pytest.mark.asyncio
async def test_ping_pong_loop_alternates_agents():
    dispatch = AsyncMock(
        return_value={
            "transcript": "did some work",
            "files_changed": ["file.py"],
            "tests_passed": False,
        }
    )

    loop = PingPongLoop(agent_a="claude", agent_b="codex", goal="Fix bug", max_rounds=4)
    result = await loop.run(dispatch_fn=dispatch)

    assert result.total_rounds == 4
    assert result.agents_used == ["claude", "codex", "claude", "codex"]
    assert not result.completed


@pytest.mark.asyncio
async def test_ping_pong_loop_stops_early_on_success():
    call_count = 0

    async def dispatch(agent, prompt):
        nonlocal call_count
        call_count += 1
        return {
            "transcript": f"round {call_count}",
            "files_changed": ["f.py"],
            "tests_passed": call_count >= 2,
        }

    loop = PingPongLoop(agent_a="claude", agent_b="codex", goal="Fix", max_rounds=6)
    result = await loop.run(dispatch_fn=dispatch)

    assert result.completed
    assert result.total_rounds == 2
    assert "Completed in 2 rounds" in result.final_status


@pytest.mark.asyncio
async def test_ping_pong_loop_passes_handoff_to_next_agent():
    prompts_received = []

    async def dispatch(agent, prompt):
        prompts_received.append((agent, prompt))
        return {
            "transcript": f"work by {agent}",
            "files_changed": [f"{agent}.py"],
            "tests_passed": False,
            "remaining_issues": [f"{agent} left issue"],
        }

    loop = PingPongLoop(agent_a="A", agent_b="B", goal="Goal", max_rounds=3)
    await loop.run(dispatch_fn=dispatch)

    # Round 2 should receive handoff from round 1
    assert "work by A" in prompts_received[1][1]
    assert "A.py" in prompts_received[1][1]
    assert "A left issue" in prompts_received[1][1]

    # Round 3 should receive handoff from round 2
    assert "work by B" in prompts_received[2][1]


@pytest.mark.asyncio
async def test_ping_pong_loop_requires_dispatch_fn():
    loop = PingPongLoop(goal="test")
    with pytest.raises(ValueError, match="dispatch_fn"):
        await loop.run()


@pytest.mark.asyncio
async def test_ping_pong_loop_includes_initial_context():
    prompts = []

    async def dispatch(agent, prompt):
        prompts.append(prompt)
        return {"transcript": "done", "tests_passed": True}

    loop = PingPongLoop(
        goal="Fix bug",
        initial_context="The bug is in line 42 of foo.py",
        max_rounds=2,
    )
    await loop.run(dispatch_fn=dispatch)

    assert "line 42" in prompts[0]
    assert "foo.py" in prompts[0]
