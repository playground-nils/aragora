"""Cross-agent dialog harness for parallel agent dispatch.

This module unblocks the 30c-Phase-D limitation: claude code, codex
CLI, and droid CLI can all answer focused review prompts non-
interactively, but only with the correct invocation flags. Previous
rounds tried ``claude --bare`` (requires explicit env-var auth) and
``codex exec`` under default ``reasoning_effort=xhigh`` (extensive
investigation chain that exceeds 90s timeouts). This harness encodes
the working flag set so future rounds always succeed.

Design contract:

- **Pure file-based state**: every dialog round is a JSONL stream;
  no in-memory long-running state, so the harness is restart-safe
  and inspectable post-hoc.
- **Agent failures are isolated**: if one agent fails, the other
  agents' turns still complete and are recorded.
- **No GitHub mutations**: the harness writes only to the local
  round directory provided by the caller.
- **Standard library only**: ``asyncio.create_subprocess_exec``,
  ``json``, ``dataclasses``, ``pathlib``. Zero new dependencies.

Usage::

    from aragora.swarm.multi_agent_dialog import (
        AgentSpec, DialogRound, dispatch_round
    )
    agents = [
        AgentSpec.claude(),
        AgentSpec.codex(),
        AgentSpec.droid(),
    ]
    round_ = DialogRound(round_id="phase-d", prompt="Review this code...")
    transcripts = await dispatch_round(round_, agents, output_dir=Path("..."))
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Verified working flag sets (round 30d agent verification)             #
# --------------------------------------------------------------------- #
#
# These are the exact CLI invocations that succeed in non-interactive
# dispatch. Encoded as data so any future round can reuse the harness
# without re-deriving the flags.

CLAUDE_FLAGS: tuple[str, ...] = ("--print",)
"""``claude --print`` works without ``--bare``. ``--bare`` requires
explicit ``ANTHROPIC_API_KEY`` env var; the keychain OAuth flow used
by interactive ``claude`` is only honored without ``--bare``."""

CODEX_FLAGS: tuple[str, ...] = (
    "exec",
    "--skip-git-repo-check",
    "-c",
    "reasoning_effort=minimal",
    "-c",
    "sandbox_mode=read-only",
)
"""``codex exec`` defaults to ``reasoning_effort=xhigh`` which produces
extensive memory/file investigation chains that exceed 90s timeouts.
``minimal`` reasoning + ``read-only`` sandbox keeps the model focused
on the prompt and skips the investigation phase."""

DROID_FLAGS: tuple[str, ...] = ("exec", "--auto", "low")
"""``droid exec --auto low`` is the read-only autonomy level: the
agent answers the prompt without taking any system-mutating actions."""


# --------------------------------------------------------------------- #
# Dataclasses                                                           #
# --------------------------------------------------------------------- #


@dataclass(frozen=True)
class AgentSpec:
    """Specification for one agent's turn in a dialog round."""

    name: str
    """Short display name (e.g. ``claude``, ``codex``, ``droid``)."""

    binary: str
    """Path to the CLI executable (or just the name if on PATH)."""

    base_flags: tuple[str, ...]
    """Flags prepended before the prompt (or before ``-`` for stdin)."""

    timeout_seconds: int
    """Hard cap on dispatch time."""

    stdin_mode: str = "argv"
    """Either ``argv`` (prompt as final arg) or ``stdin`` (piped to stdin)."""

    @classmethod
    def claude(cls, timeout_seconds: int = 60) -> "AgentSpec":
        return cls(
            name="claude",
            binary="claude",
            base_flags=CLAUDE_FLAGS,
            timeout_seconds=timeout_seconds,
            stdin_mode="stdin",
        )

    @classmethod
    def codex(cls, timeout_seconds: int = 90) -> "AgentSpec":
        return cls(
            name="codex",
            binary="codex",
            base_flags=CODEX_FLAGS,
            timeout_seconds=timeout_seconds,
            stdin_mode="stdin",
        )

    @classmethod
    def droid(cls, timeout_seconds: int = 60) -> "AgentSpec":
        return cls(
            name="droid",
            binary="droid",
            base_flags=DROID_FLAGS,
            timeout_seconds=timeout_seconds,
            stdin_mode="stdin",
        )


@dataclass
class DialogTurn:
    """One agent's response for one prompt."""

    agent: str
    started_at: str
    finished_at: str
    elapsed_seconds: float
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    error: str | None = None

    def succeeded(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.error

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class DialogRound:
    """One round of cross-agent dialog: a single prompt for many agents."""

    round_id: str
    prompt: str
    extra_context: str = ""
    """Optional extra context (e.g. source file contents) appended to prompt."""

    metadata: dict[str, str] = field(default_factory=dict)

    def render_prompt(self) -> str:
        if self.extra_context:
            return f"{self.prompt}\n\n{self.extra_context}"
        return self.prompt


# --------------------------------------------------------------------- #
# Dispatch                                                              #
# --------------------------------------------------------------------- #


async def _dispatch_one(
    spec: AgentSpec,
    rendered_prompt: str,
) -> DialogTurn:
    """Dispatch one agent and return a recorded ``DialogTurn``.

    Errors (subprocess launch failure, timeout) are caught and
    encoded into the turn rather than propagated. This guarantees
    that one agent's failure cannot cascade.
    """
    started_at = datetime.now(timezone.utc)

    if spec.stdin_mode == "stdin":
        argv = [spec.binary, *spec.base_flags]
        stdin_data: bytes | None = rendered_prompt.encode("utf-8")
    else:
        argv = [spec.binary, *spec.base_flags, rendered_prompt]
        stdin_data = None

    timed_out = False
    err_msg: str | None = None
    rc = -1
    out = ""
    err = ""

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE if stdin_data is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out_b, err_b = await asyncio.wait_for(
                proc.communicate(input=stdin_data),
                timeout=spec.timeout_seconds,
            )
            rc = proc.returncode if proc.returncode is not None else -1
            out = out_b.decode("utf-8", errors="replace")
            err = err_b.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            timed_out = True
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
    except FileNotFoundError:
        err_msg = f"binary not found: {spec.binary}"
        logger.warning("multi_agent_dialog: %s", err_msg)
    except Exception as exc:  # noqa: BLE001 — capture any subprocess setup error
        err_msg = f"dispatch failed: {type(exc).__name__}: {exc}"
        logger.warning("multi_agent_dialog: %s", err_msg)

    finished_at = datetime.now(timezone.utc)
    elapsed = (finished_at - started_at).total_seconds()

    return DialogTurn(
        agent=spec.name,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        elapsed_seconds=round(elapsed, 3),
        returncode=rc,
        stdout=out,
        stderr=err,
        timed_out=timed_out,
        error=err_msg,
    )


async def dispatch_round(
    round_: DialogRound,
    agents: Sequence[AgentSpec],
) -> list[DialogTurn]:
    """Dispatch all agents in parallel; return turn records.

    Failures of any single agent do not affect the others.
    """
    if not agents:
        return []
    rendered = round_.render_prompt()
    tasks = [_dispatch_one(spec, rendered) for spec in agents]
    return list(await asyncio.gather(*tasks))


# --------------------------------------------------------------------- #
# Persistence                                                           #
# --------------------------------------------------------------------- #


def write_round_jsonl(
    round_: DialogRound,
    turns: Sequence[DialogTurn],
    output_dir: Path,
) -> Path:
    """Persist round + turns as a JSONL stream under ``output_dir``.

    The first line is the round metadata. Subsequent lines are turns.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"dialog-{round_.round_id}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "type": "round",
                    "round_id": round_.round_id,
                    "prompt": round_.prompt,
                    "extra_context_chars": len(round_.extra_context),
                    "metadata": round_.metadata,
                },
                sort_keys=True,
            )
            + "\n"
        )
        for turn in turns:
            payload = {"type": "turn", **turn.to_json()}
            f.write(json.dumps(payload, sort_keys=True) + "\n")
    return out_path


def render_transcript_markdown(
    round_: DialogRound,
    turns: Sequence[DialogTurn],
) -> str:
    """Render round + turns as a single markdown transcript."""
    lines: list[str] = [
        f"# Cross-agent dialog — round `{round_.round_id}`",
        "",
        f"_Prompt size: {len(round_.prompt)} chars; extra context: "
        f"{len(round_.extra_context)} chars._",
        "",
        "## Prompt",
        "",
        "```",
        round_.prompt.strip() or "(empty)",
        "```",
        "",
    ]
    if round_.extra_context.strip():
        lines.extend(
            [
                "## Extra context",
                "",
                "```",
                round_.extra_context.strip()[:2000]
                + ("..." if len(round_.extra_context) > 2000 else ""),
                "```",
                "",
            ]
        )

    success_count = sum(1 for t in turns if t.succeeded())
    lines.extend(
        [
            "## Summary",
            "",
            f"- Agents dispatched: **{len(turns)}**",
            f"- Successful: **{success_count}**",
            f"- Failed: **{len(turns) - success_count}**",
            "",
        ]
    )

    lines.extend(["## Per-agent responses", ""])
    for turn in turns:
        status = "succeeded" if turn.succeeded() else "FAILED"
        lines.extend(
            [
                f"### `{turn.agent}` — {status} (rc={turn.returncode}, "
                f"{turn.elapsed_seconds:.1f}s, "
                f"timed_out={turn.timed_out})",
                "",
            ]
        )
        if turn.error:
            lines.extend([f"_Error: {turn.error}_", ""])
        if turn.stdout.strip():
            lines.extend(
                [
                    "**stdout:**",
                    "",
                    "```",
                    turn.stdout.rstrip(),
                    "```",
                    "",
                ]
            )
        if turn.stderr.strip() and not turn.succeeded():
            tail = "\n".join(turn.stderr.rstrip().splitlines()[-10:])
            lines.extend(
                [
                    "**stderr (last 10 lines):**",
                    "",
                    "```",
                    tail,
                    "```",
                    "",
                ]
            )
    return "\n".join(lines)


def write_transcript_markdown(
    round_: DialogRound,
    turns: Sequence[DialogTurn],
    output_dir: Path,
) -> Path:
    """Persist a markdown transcript and return its path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"dialog-{round_.round_id}.md"
    out_path.write_text(render_transcript_markdown(round_, turns), encoding="utf-8")
    return out_path


# --------------------------------------------------------------------- #
# Convenience high-level entry point                                    #
# --------------------------------------------------------------------- #


async def run_round_and_persist(
    round_: DialogRound,
    agents: Sequence[AgentSpec],
    output_dir: Path,
) -> tuple[Path, Path, list[DialogTurn]]:
    """Dispatch the round, persist JSONL + markdown, return both paths and turns."""
    turns = await dispatch_round(round_, agents)
    jsonl_path = write_round_jsonl(round_, turns, output_dir)
    md_path = write_transcript_markdown(round_, turns, output_dir)
    return jsonl_path, md_path, turns
