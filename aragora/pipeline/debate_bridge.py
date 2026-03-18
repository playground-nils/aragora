"""Debate Outcome → Pipeline Stage Bridge.

Extracts actionable workflow hints from completed debate results so that
downstream pipeline stages (workflow configuration, execution planning)
can be pre-populated with debate-derived intelligence.

Part of the Decision Integrity Kernel unification (#811).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DebateOutcomeBridge:
    """Extracts workflow hints from debate results for pipeline stage transitions."""

    def extract_workflow_hints(self, debate_result: dict[str, Any]) -> dict[str, Any]:
        """Extract actionable workflow hints from a completed debate.

        Args:
            debate_result: Dict containing debate outcome data.  Expected
                keys include ``agent_scores``, ``dissent``,
                ``consensus_claims``, and ``rounds_completed``.

        Returns:
            Dict with keys: ``recommended_agents``, ``risk_factors``,
            ``dissent_summary``, ``acceptance_criteria``,
            ``estimated_complexity``.
        """
        hints: dict[str, Any] = {
            "recommended_agents": [],
            "risk_factors": [],
            "dissent_summary": "",
            "acceptance_criteria": [],
            "estimated_complexity": "medium",
        }

        # Extract top-performing agents from scores
        agent_scores = debate_result.get("agent_scores")
        if isinstance(agent_scores, dict) and agent_scores:
            sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
            hints["recommended_agents"] = [agent for agent, _score in sorted_agents[:3]]

        # Extract risk factors from dissent
        dissent = debate_result.get("dissent")
        if isinstance(dissent, list) and dissent:
            hints["risk_factors"] = [
                d.get("concern", str(d)) if isinstance(d, dict) else str(d) for d in dissent
            ]
            hints["dissent_summary"] = f"{len(dissent)} agent(s) dissented"

        # Extract acceptance criteria from consensus claims
        consensus_claims = debate_result.get("consensus_claims")
        if isinstance(consensus_claims, list):
            hints["acceptance_criteria"] = [
                c.get("claim", str(c)) if isinstance(c, dict) else str(c) for c in consensus_claims
            ]

        # Estimate complexity from round count
        rounds = debate_result.get("rounds_completed")
        if rounds is not None and isinstance(rounds, (int, float)):
            if rounds <= 2:
                hints["estimated_complexity"] = "low"
            elif rounds >= 5:
                hints["estimated_complexity"] = "high"
            # else stays "medium"

        return hints
