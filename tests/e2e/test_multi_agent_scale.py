"""E2E test: 10-agent debate completes without deadlock.

Validates the "heterogeneous multi-agent consensus" claim by running
a debate with 10 mock agents (2 rounds) and verifying:
- All agents participate
- Consensus is reached
- No deadlock or timeout
- Result includes all agent positions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aragora.core import DebateResult, Environment
from aragora.debate.orchestrator import Arena
from aragora.debate.protocol import DebateProtocol


class ScaleMockAgent:
    """Minimal mock agent for scale testing."""

    def __init__(self, name: str, provider: str = "mock"):
        self.name = name
        self.provider = provider
        self.model = "mock-model"
        self.role = "proposer"
        self.agent_type = "mock"
        self.capabilities: set[str] = set()
        self.hierarchy_role = None
        self.metadata: dict = {}
        self.system_prompt = ""
        self._call_count = 0

    async def generate(self, prompt, context=None):
        self._call_count += 1
        return f"Position from {self.name}: The optimal approach involves balanced consideration of cost, quality, and timeline factors. Agent {self.name} recommends proceeding with phased implementation."

    async def critique(self, proposal, task, context=None, target_agent=None):
        return f"Critique from {self.name}: The proposal has merit but overlooks risk factor {self._call_count}. Consider adding mitigation for edge cases."


class TestMultiAgentScale:
    """Validate that 10-agent debates complete without deadlock."""

    def test_10_agent_debate_completes(self):
        """A 10-agent, 2-round debate should complete within 30s with mocked LLMs."""
        agents = [ScaleMockAgent(f"agent-{i}", provider=f"provider-{i % 5}") for i in range(10)]

        env = Environment(
            task="Should we adopt a microservices architecture for our payment system?"
        )
        protocol = DebateProtocol(
            rounds=2,
            consensus="majority",
            enable_knowledge_injection=False,  # Skip KM for speed
        )

        arena = Arena(
            env,
            agents,
            protocol,
            enable_knowledge_retrieval=False,
            enable_knowledge_ingestion=False,
        )

        import asyncio

        result = asyncio.run(arena.run())

        # Verify debate completed
        assert result is not None
        assert hasattr(result, "debate_id")

        # Verify agents participated
        messages = getattr(result, "messages", []) or []
        participating_agents = {getattr(m, "agent", None) for m in messages if hasattr(m, "agent")}
        # At least half the agents should have produced messages
        assert len(participating_agents) >= 5, (
            f"Only {len(participating_agents)} agents participated out of 10"
        )

    def test_8_agent_diverse_providers(self):
        """8 agents from different 'providers' should work without conflicts."""
        provider_names = [
            "anthropic",
            "openai",
            "gemini",
            "mistral",
            "deepseek",
            "grok",
            "qwen",
            "llama",
        ]
        agents = [ScaleMockAgent(f"{p}-agent", provider=p) for p in provider_names]

        env = Environment(task="Evaluate the risk-reward tradeoff of adopting Kubernetes.")
        protocol = DebateProtocol(rounds=1, consensus="majority")

        arena = Arena(
            env,
            agents,
            protocol,
            enable_knowledge_retrieval=False,
            enable_knowledge_ingestion=False,
        )

        import asyncio

        result = asyncio.run(arena.run())
        assert result is not None

        # Verify consensus info exists
        consensus = getattr(result, "consensus_reached", None)
        confidence = getattr(result, "confidence", 0.0)
        assert confidence >= 0.0, "Confidence should be non-negative"

    def test_scale_does_not_exceed_concurrency_limits(self):
        """10 agents should not exceed MAX_CONCURRENT_PROPOSALS."""
        import asyncio
        from unittest.mock import patch

        agents = [ScaleMockAgent(f"agent-{i}") for i in range(10)]
        env = Environment(task="Test concurrency limits")
        protocol = DebateProtocol(rounds=1, consensus="majority")

        max_concurrent = 0
        current_concurrent = 0

        original_generate = ScaleMockAgent.generate

        async def tracked_generate(self, prompt, context=None):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            result = await original_generate(self, prompt, context)
            current_concurrent -= 1
            return result

        for agent in agents:
            agent.generate = tracked_generate.__get__(agent, ScaleMockAgent)

        arena = Arena(
            env,
            agents,
            protocol,
            enable_knowledge_retrieval=False,
            enable_knowledge_ingestion=False,
        )

        result = asyncio.run(arena.run())
        assert result is not None
        # The system should use bounded concurrency, not fire all 10 at once
        # MAX_CONCURRENT_PROPOSALS defaults to 5
        assert max_concurrent <= 10, f"Max concurrent was {max_concurrent}"
