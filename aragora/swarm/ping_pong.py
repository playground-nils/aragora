"""Ping-pong orchestration: two AI systems prompt each other alternately.

Each system acts as implementer and reviewer. The outgoing system produces
a transcript of work done plus a follow-up prompt for the incoming system.
This pattern prevents drift, provides implicit review checkpoints, and
leverages different failure modes across model families.

Usage:
    loop = PingPongLoop(
        agent_a="claude",
        agent_b="codex",
        goal="Fix the 5 failing tests in tests/debate/",
    )
    result = await loop.run(max_rounds=3)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

UTC = timezone.utc


@dataclass
class PingPongRound:
    """One round of ping-pong: agent works, produces transcript + handoff."""

    round_number: int
    agent: str  # "claude" or "codex"
    input_prompt: str
    transcript: str = ""
    handoff_prompt: str = ""
    files_changed: list[str] = field(default_factory=list)
    tests_passed: bool = False
    elapsed_seconds: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class PingPongResult:
    """Result of a complete ping-pong loop."""

    goal: str
    rounds: list[PingPongRound] = field(default_factory=list)
    completed: bool = False
    final_status: str = ""

    @property
    def total_rounds(self) -> int:
        return len(self.rounds)

    @property
    def agents_used(self) -> list[str]:
        return [r.agent for r in self.rounds]


def build_handoff_prompt(
    *,
    goal: str,
    previous_transcript: str,
    previous_agent: str,
    next_agent: str,
    round_number: int,
    files_changed: list[str] | None = None,
    remaining_issues: list[str] | None = None,
) -> str:
    """Build the prompt that one agent hands off to the next.

    This is the key innovation: the outgoing agent's transcript becomes
    structured context for the incoming agent, with an explicit follow-up
    task that prevents drift.
    """
    sections = [
        f"## Goal\n{goal}",
        "",
        f"## Context (from {previous_agent}, round {round_number})",
        f"The previous agent ({previous_agent}) worked on this and produced the following:",
        "",
        "### Work Done",
        previous_transcript[:3000] if previous_transcript else "(no transcript available)",
        "",
    ]

    if files_changed:
        sections.append("### Files Changed")
        for f in files_changed[:20]:
            sections.append(f"- {f}")
        sections.append("")

    if remaining_issues:
        sections.append("### Remaining Issues")
        for issue in remaining_issues[:10]:
            sections.append(f"- {issue}")
        sections.append("")

    sections.extend(
        [
            f"## Your Task ({next_agent}, round {round_number + 1})",
            "1. Review what the previous agent did",
            "2. Verify their changes work (run the relevant tests)",
            "3. Fix any issues found",
            "4. If tests pass, commit and describe what you did",
            "5. If there's remaining work, describe it clearly for the next handoff",
            "",
            "## Rules",
            "- Do NOT redo work that's already correct",
            "- Fix only what's broken or incomplete",
            "- Commit your changes with `git add -A && git commit -m 'description'`",
            "- End with a clear summary of what you did and what remains",
        ]
    )

    return "\n".join(sections)


class PingPongLoop:
    """Orchestrate alternating work between two AI agent types.

    Each round:
    1. Agent A receives a prompt (initial goal or handoff from Agent B)
    2. Agent A works, produces transcript + files changed
    3. Build handoff prompt from A's output for Agent B
    4. Agent B receives handoff prompt
    5. Agent B works, produces transcript + files changed
    6. Build handoff prompt from B's output for Agent A
    7. Repeat until goal is met or max rounds reached
    """

    def __init__(
        self,
        *,
        agent_a: str = "claude",
        agent_b: str = "codex",
        goal: str,
        initial_context: str = "",
        max_rounds: int = 3,
    ) -> None:
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.goal = goal
        self.initial_context = initial_context
        self.max_rounds = max_rounds
        self.rounds: list[PingPongRound] = []

    async def run(
        self,
        *,
        dispatch_fn: Any = None,
    ) -> PingPongResult:
        """Run the ping-pong loop.

        Args:
            dispatch_fn: Async function(agent: str, prompt: str) -> dict
                         with keys: transcript, files_changed, tests_passed
        """
        if dispatch_fn is None:
            raise ValueError("dispatch_fn is required")

        current_prompt = self._build_initial_prompt()
        agents = [self.agent_a, self.agent_b]

        for round_num in range(self.max_rounds):
            agent = agents[round_num % 2]
            next_agent = agents[(round_num + 1) % 2]

            logger.info(
                "ping_pong round=%d agent=%s goal=%s",
                round_num + 1,
                agent,
                self.goal[:60],
            )

            # Dispatch work to current agent
            result = await dispatch_fn(agent, current_prompt)

            round_record = PingPongRound(
                round_number=round_num + 1,
                agent=agent,
                input_prompt=current_prompt[:500],
                transcript=str(result.get("transcript", "")),
                handoff_prompt="",
                files_changed=list(result.get("files_changed", [])),
                tests_passed=bool(result.get("tests_passed", False)),
            )
            self.rounds.append(round_record)

            # Check if we're done
            if round_record.tests_passed and round_num >= 1:
                logger.info("ping_pong completed: tests pass after round %d", round_num + 1)
                return PingPongResult(
                    goal=self.goal,
                    rounds=list(self.rounds),
                    completed=True,
                    final_status=f"Completed in {round_num + 1} rounds",
                )

            # Build handoff prompt for next agent
            current_prompt = build_handoff_prompt(
                goal=self.goal,
                previous_transcript=round_record.transcript,
                previous_agent=agent,
                next_agent=next_agent,
                round_number=round_num + 1,
                files_changed=round_record.files_changed,
                remaining_issues=result.get("remaining_issues", []),
            )
            round_record.handoff_prompt = current_prompt[:500]

        return PingPongResult(
            goal=self.goal,
            rounds=list(self.rounds),
            completed=False,
            final_status=f"Max rounds ({self.max_rounds}) reached",
        )

    def _build_initial_prompt(self) -> str:
        sections = [
            f"## Goal\n{self.goal}",
        ]
        if self.initial_context:
            sections.extend(
                [
                    "",
                    "## Context",
                    self.initial_context[:2000],
                ]
            )
        sections.extend(
            [
                "",
                "## Instructions",
                "1. Implement the goal",
                "2. Run relevant tests to verify",
                "3. Commit your changes",
                "4. Summarize what you did and what remains",
            ]
        )
        return "\n".join(sections)
