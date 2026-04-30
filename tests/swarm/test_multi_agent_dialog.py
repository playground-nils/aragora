"""Tests for aragora.swarm.multi_agent_dialog."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from aragora.swarm.multi_agent_dialog import (
    CLAUDE_FLAGS,
    CODEX_FLAGS,
    DROID_FLAGS,
    AgentSpec,
    DialogRound,
    DialogTurn,
    dispatch_round,
    render_transcript_markdown,
    run_round_and_persist,
    write_round_jsonl,
    write_transcript_markdown,
    _dispatch_one,
)


def test_agent_spec_claude_flags() -> None:
    spec = AgentSpec.claude()
    assert spec.name == "claude"
    assert spec.binary == "claude"
    assert spec.base_flags == CLAUDE_FLAGS
    assert spec.stdin_mode == "stdin"
    assert spec.timeout_seconds == 60


def test_agent_spec_codex_flags_include_minimal_reasoning() -> None:
    spec = AgentSpec.codex()
    assert "reasoning_effort=minimal" in spec.base_flags
    assert "sandbox_mode=read-only" in spec.base_flags
    assert spec.timeout_seconds == 90


def test_agent_spec_droid_flags_include_auto_low() -> None:
    spec = AgentSpec.droid()
    assert "exec" in spec.base_flags
    assert "low" in spec.base_flags
    assert "--auto" in spec.base_flags


def test_agent_spec_custom_timeout() -> None:
    spec = AgentSpec.claude(timeout_seconds=30)
    assert spec.timeout_seconds == 30


def test_dialog_round_render_prompt_no_context() -> None:
    r = DialogRound(round_id="t", prompt="hello")
    assert r.render_prompt() == "hello"


def test_dialog_round_render_prompt_with_context() -> None:
    r = DialogRound(round_id="t", prompt="hello", extra_context="more info")
    assert "hello" in r.render_prompt()
    assert "more info" in r.render_prompt()


def test_dialog_turn_succeeded_clean() -> None:
    t = DialogTurn(
        agent="x",
        started_at="2026-04-30T00:00:00+00:00",
        finished_at="2026-04-30T00:00:01+00:00",
        elapsed_seconds=1.0,
        returncode=0,
        stdout="OK",
        stderr="",
        timed_out=False,
        error=None,
    )
    assert t.succeeded()


def test_dialog_turn_succeeded_false_on_timeout() -> None:
    t = DialogTurn(
        agent="x",
        started_at="t1",
        finished_at="t2",
        elapsed_seconds=60.0,
        returncode=0,
        stdout="",
        stderr="",
        timed_out=True,
    )
    assert not t.succeeded()


def test_dialog_turn_succeeded_false_on_error() -> None:
    t = DialogTurn(
        agent="x",
        started_at="t1",
        finished_at="t2",
        elapsed_seconds=0.0,
        returncode=-1,
        stdout="",
        stderr="",
        timed_out=False,
        error="binary not found",
    )
    assert not t.succeeded()


def test_dialog_turn_succeeded_false_on_nonzero_rc() -> None:
    t = DialogTurn(
        agent="x",
        started_at="t1",
        finished_at="t2",
        elapsed_seconds=1.0,
        returncode=1,
        stdout="",
        stderr="boom",
        timed_out=False,
    )
    assert not t.succeeded()


@pytest.mark.asyncio
async def test_dispatch_one_succeeds_with_echo() -> None:
    spec = AgentSpec(
        name="echo",
        binary="/bin/sh",
        base_flags=("-c", "cat"),
        timeout_seconds=10,
        stdin_mode="stdin",
    )
    turn = await _dispatch_one(spec, rendered_prompt="hello")
    assert turn.succeeded()
    assert "hello" in turn.stdout
    assert turn.returncode == 0


@pytest.mark.asyncio
async def test_dispatch_one_handles_missing_binary() -> None:
    spec = AgentSpec(
        name="missing",
        binary="/no/such/binary-9b13c2e4",
        base_flags=(),
        timeout_seconds=5,
        stdin_mode="stdin",
    )
    turn = await _dispatch_one(spec, rendered_prompt="hi")
    assert not turn.succeeded()
    assert turn.error is not None
    assert "binary not found" in turn.error


@pytest.mark.asyncio
async def test_dispatch_one_handles_timeout() -> None:
    spec = AgentSpec(
        name="sleeper",
        binary="/bin/sh",
        base_flags=("-c", "sleep 5"),
        timeout_seconds=1,
        stdin_mode="argv",
    )
    turn = await _dispatch_one(spec, rendered_prompt="x")
    assert turn.timed_out
    assert not turn.succeeded()


@pytest.mark.asyncio
async def test_dispatch_round_isolates_failures() -> None:
    """A failing agent must not break the others."""
    good = AgentSpec(
        name="good",
        binary="/bin/sh",
        base_flags=("-c", "echo OK"),
        timeout_seconds=5,
        stdin_mode="argv",
    )
    bad = AgentSpec(
        name="bad",
        binary="/no/such/binary-9b13c2e4",
        base_flags=(),
        timeout_seconds=5,
        stdin_mode="argv",
    )
    round_ = DialogRound(round_id="t", prompt="hi")
    turns = await dispatch_round(round_, [good, bad])
    assert len(turns) == 2
    by_agent = {t.agent: t for t in turns}
    assert by_agent["good"].succeeded()
    assert not by_agent["bad"].succeeded()


@pytest.mark.asyncio
async def test_dispatch_round_empty_agents() -> None:
    round_ = DialogRound(round_id="t", prompt="hi")
    turns = await dispatch_round(round_, [])
    assert turns == []


def test_write_round_jsonl_creates_file(tmp_path: Path) -> None:
    round_ = DialogRound(round_id="r1", prompt="p")
    turns = [
        DialogTurn(
            agent="a",
            started_at="t1",
            finished_at="t2",
            elapsed_seconds=1.0,
            returncode=0,
            stdout="x",
            stderr="",
            timed_out=False,
        )
    ]
    out = write_round_jsonl(round_, turns, tmp_path)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    head = json.loads(lines[0])
    assert head["type"] == "round"
    assert head["round_id"] == "r1"
    body = json.loads(lines[1])
    assert body["type"] == "turn"
    assert body["agent"] == "a"


def test_render_transcript_markdown_includes_summary() -> None:
    round_ = DialogRound(round_id="r1", prompt="Review this")
    turns = [
        DialogTurn(
            agent="a1",
            started_at="t1",
            finished_at="t2",
            elapsed_seconds=1.0,
            returncode=0,
            stdout="great work",
            stderr="",
            timed_out=False,
        ),
        DialogTurn(
            agent="a2",
            started_at="t1",
            finished_at="t2",
            elapsed_seconds=2.0,
            returncode=1,
            stdout="",
            stderr="oops",
            timed_out=False,
        ),
    ]
    md = render_transcript_markdown(round_, turns)
    assert "Cross-agent dialog" in md
    assert "Successful: **1**" in md
    assert "Failed: **1**" in md
    assert "great work" in md
    assert "FAILED" in md


def test_render_transcript_markdown_with_extra_context() -> None:
    round_ = DialogRound(round_id="r1", prompt="Review", extra_context="some source")
    md = render_transcript_markdown(round_, [])
    assert "Extra context" in md
    assert "some source" in md


def test_write_transcript_markdown_creates_file(tmp_path: Path) -> None:
    round_ = DialogRound(round_id="r1", prompt="p")
    out = write_transcript_markdown(round_, [], tmp_path)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "Cross-agent dialog" in body


@pytest.mark.asyncio
async def test_run_round_and_persist_end_to_end(tmp_path: Path) -> None:
    spec = AgentSpec(
        name="echo",
        binary="/bin/sh",
        base_flags=("-c", "echo HELLO"),
        timeout_seconds=5,
        stdin_mode="argv",
    )
    round_ = DialogRound(round_id="e2e", prompt="ping")
    jsonl_path, md_path, turns = await run_round_and_persist(round_, [spec], tmp_path)
    assert jsonl_path.exists()
    assert md_path.exists()
    assert len(turns) == 1
    assert turns[0].succeeded()
    md = md_path.read_text(encoding="utf-8")
    assert "HELLO" in md


def test_constants_match_round_30d_verification() -> None:
    """These flag tuples are the exact verified-working flag sets.

    If any of these change, the round's agent_dispatch_verification step
    must be re-run before merging."""
    assert CLAUDE_FLAGS == ("--print",)
    assert "reasoning_effort=minimal" in CODEX_FLAGS
    assert "sandbox_mode=read-only" in CODEX_FLAGS
    assert "--skip-git-repo-check" in CODEX_FLAGS
    assert DROID_FLAGS == ("exec", "--auto", "low")
